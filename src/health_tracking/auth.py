import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler to capture OAuth callback."""

    def do_GET(self) -> None:
        """Handle GET request containing OAuth callback."""
        # Parse the URL and extract the code parameter
        query_components = parse_qs(urlparse(self.path).query)
        code = query_components.get("code", [None])[0]

        if code:
            self.server.code = code  # type: ignore

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html_content = """
            <html>
            <head><title>Authentication Successful</title></head>
            <body>
                <h1>Authentication Successful!</h1>
                <p>You can now close this window and return to the application.</p>
            </body>
            </html>
            """
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html_content = """
            <html>
            <head><title>Authentication Failed</title></head>
            <body>
                <h1>Authentication Failed</h1>
                <p>No authorization code was received. Please try again.</p>
            </body>
            </html>
            """

        self.wfile.write(html_content.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP server logging."""
        return


class AuthHTTPServer(HTTPServer):
    """A local server to receive the OAuth callback."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.code: Optional[str] = None

    @classmethod
    def run(cls, port: int) -> "AuthHTTPServer":
        server = cls(("localhost", port), OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server


def run_oauth_flow(
    auth_url: str, port: int = 8080, timeout_seconds: int = 300
) -> Optional[str]:
    """
    Run an OAuth flow with browser-based authentication.

    Args:
        auth_url: The authorization URL to open in the browser
        port: Port to use for the local callback server
        timeout_seconds: Maximum time to wait for authorization (in seconds)

    Returns:
        The authorization code if successful, None if timed out
    """
    server = AuthHTTPServer.run(port)

    try:
        print("\nOpening browser for authorization...")
        webbrowser.open(auth_url)

        print("Waiting for authorization to complete...")
        waited = 0
        while server.code is None and waited < timeout_seconds:
            time.sleep(1)
            waited += 1
            # Print a message every 30 seconds
            if waited % 30 == 0:
                print(f"Still waiting for authorization... ({waited} seconds)")

        if server.code is None:
            print("Error: Timed out waiting for authorization.")
            return None

        print("Authorization code received successfully!")
        return server.code

    finally:
        # Shutdown the server
        server.shutdown()
        server.server_close()

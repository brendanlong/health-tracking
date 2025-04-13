import os
import sys
from urllib.parse import urlparse, parse_qs
from fitbit.api import Fitbit

# Get Fitbit credentials from environment variables
CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/"


def get_fitbit_client() -> Fitbit:
    """Get Fitbit tokens using authorization code flow with manual copy-paste."""

    # Check for required credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "Error: FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET environment variables must be set."
        )
        sys.exit(1)

    # Create the OAuth2 client
    fitbit = Fitbit(CLIENT_ID, CLIENT_SECRET, timeout=10)

    # Generate authorization URL
    auth_url, _ = fitbit.client.authorize_token_url()

    # Instruct user to authorize the app
    print("\n1. Go to this URL in your browser:")
    print(f"\n{auth_url}\n")
    print("2. Authorize the app and you'll be redirected to a URL.")
    print("3. Copy that URL and paste it below, even if it shows an error page.\n")

    # Get the redirect URL from user
    redirect_url = input("Paste the redirect URL here: ")

    # Parse the authorization code from the redirect URL
    parsed_url = urlparse(redirect_url)
    code = parse_qs(parsed_url.query).get("code", [None])[0]

    if not code:
        print("Error: No authorization code found in the URL.")
        sys.exit(1)

    # Exchange authorization code for tokens
    fitbit.client.fetch_access_token(code)

    return fitbit


if __name__ == "__main__":
    get_fitbit_client()

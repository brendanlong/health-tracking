import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, TypedDict, cast


class AWSContext(TypedDict, total=False):
    """Lambda context object type hint."""

    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    aws_request_id: str
    log_group_name: str
    log_stream_name: str


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(secret_name: str) -> str:
    """
    Retrieve a secret from AWS Secrets Manager
    """
    # boto3 and botocore will be available in the Lambda environment
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore

    if not secret_name:
        raise ValueError("Secret name cannot be empty")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise e

    return get_secret_value_response["SecretString"]


def setup_oauth_tokens() -> None:
    """
    Set up OAuth tokens from AWS Secrets Manager
    """
    # Get environment variables for secret names
    google_token_secret_name = os.environ.get("GOOGLE_TOKEN_SECRET_NAME")
    fitbit_token_secret_name = os.environ.get("FITBIT_TOKEN_SECRET_NAME")
    fitbit_client_id_secret_name = os.environ.get("FITBIT_CLIENT_ID_SECRET_NAME")
    fitbit_client_secret_secret_name = os.environ.get(
        "FITBIT_CLIENT_SECRET_SECRET_NAME"
    )

    if not google_token_secret_name:
        raise ValueError("GOOGLE_TOKEN_SECRET_NAME environment variable not set")
    if not fitbit_token_secret_name:
        raise ValueError("FITBIT_TOKEN_SECRET_NAME environment variable not set")
    if not fitbit_client_id_secret_name:
        raise ValueError("FITBIT_CLIENT_ID_SECRET_NAME environment variable not set")
    if not fitbit_client_secret_secret_name:
        raise ValueError(
            "FITBIT_CLIENT_SECRET_SECRET_NAME environment variable not set"
        )

    # Get the credential paths from environment or use defaults
    google_token_path = os.environ.get(
        "GOOGLE_TOKEN_PATH", "/tmp/credentials/google_token.json"
    )
    fitbit_token_path = os.environ.get(
        "FITBIT_TOKEN_PATH", "/tmp/credentials/fitbit_token.json"
    )

    # Make sure the directory exists
    Path(google_token_path).parent.mkdir(parents=True, exist_ok=True)

    # Retrieve and save Google token
    logger.info(f"Retrieving Google token from {google_token_secret_name}")
    google_token = get_secret(google_token_secret_name)
    with open(google_token_path, "w") as f:
        f.write(google_token)
    logger.info(f"Saved Google token to {google_token_path}")

    # Retrieve and save Fitbit token
    logger.info(f"Retrieving Fitbit token from {fitbit_token_secret_name}")
    fitbit_token = get_secret(fitbit_token_secret_name)
    with open(fitbit_token_path, "w") as f:
        f.write(fitbit_token)
    logger.info(f"Saved Fitbit token to {fitbit_token_path}")

    # Retrieve and set Fitbit client ID and secret as environment variables
    logger.info(f"Retrieving Fitbit client ID from {fitbit_client_id_secret_name}")
    fitbit_client_id = get_secret(fitbit_client_id_secret_name)
    os.environ["FITBIT_CLIENT_ID"] = fitbit_client_id
    logger.info("Set FITBIT_CLIENT_ID environment variable")

    logger.info(
        f"Retrieving Fitbit client secret from {fitbit_client_secret_secret_name}"
    )
    fitbit_client_secret = get_secret(fitbit_client_secret_secret_name)
    os.environ["FITBIT_CLIENT_SECRET"] = fitbit_client_secret
    logger.info("Set FITBIT_CLIENT_SECRET environment variable")


def handler(event: Dict[str, Any], context: AWSContext) -> Dict[str, Any]:
    """
    Lambda handler function
    """
    logger.info("Starting health data sync")

    try:
        # Get configuration from environment or event
        sync_type = os.environ.get("SYNC_TYPE") or event.get("sync_type")
        spreadsheet_id = os.environ.get("SPREADSHEET_ID") or event.get("spreadsheet_id")
        sheet_name = os.environ.get("SHEET_NAME") or event.get("sheet_name")

        if not all([sync_type, spreadsheet_id, sheet_name]):
            raise ValueError(
                "Missing required parameters: sync_type, spreadsheet_id, sheet_name"
            )

        # Set up OAuth tokens from AWS Secrets Manager
        setup_oauth_tokens()

        # Build command for sync script
        lambda_task_root = os.environ.get("LAMBDA_TASK_ROOT", "")
        script_path = os.path.join(lambda_task_root, "bin/fitbit-sheets-sync.py")

        # Use explicit strings for command to satisfy type checker
        cmd: List[str] = [
            script_path,
            "--spreadsheet-id",
            cast(str, spreadsheet_id),
            "--sheet-name",
            cast(str, sheet_name),
            "--type",
            cast(str, sync_type),
            "--no-color",
        ]

        # Execute sync script with environment variables
        logger.info(f"Executing command: {' '.join(cmd)}")
        # Create a copy of the current environment and update it
        env = os.environ.copy()
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=env, timeout=30
        )

        # Log result
        logger.info("Sync completed successfully")
        logger.info(f"Output: {result.stdout}")

        # Log stderr even if the command succeeded (it may contain warnings)
        if result.stderr:
            logger.warning(f"Stderr output: {result.stderr}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Health data sync completed successfully",
                    "sync_type": sync_type,
                    "sheet_name": sheet_name,
                }
            ),
        }

    except subprocess.TimeoutExpired as e:
        logger.error(f"Command {e.cmd} timed out after {e.timeout} seconds")
        logger.error(f"Stdout: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
        logger.error(f"Stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        return {
            "statusCode": 504,
            "body": json.dumps(
                {
                    "message": f"Health data sync timed out after {e.timeout} seconds",
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": e.stderr if hasattr(e, "stderr") else "",
                }
            ),
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Command {e.cmd} failed with exit code {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": f"Error during health data sync: {str(e)}",
                    "stdout": e.stdout,
                    "stderr": e.stderr,
                }
            ),
        }
    except Exception as e:
        logger.error(f"Error during health data sync: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error during health data sync: {str(e)}"}),
        }

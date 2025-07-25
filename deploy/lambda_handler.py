import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, TypedDict, cast

# boto3 and botocore will be available in the Lambda environment
import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore

# Environment variable constants
GOOGLE_TOKEN_SECRET_NAME = os.environ.get("GOOGLE_TOKEN_SECRET_NAME")
FITBIT_TOKEN_SECRET_NAME = os.environ.get("FITBIT_TOKEN_SECRET_NAME")
FITBIT_CLIENT_ID_SECRET_NAME = os.environ.get("FITBIT_CLIENT_ID_SECRET_NAME")
FITBIT_CLIENT_SECRET_SECRET_NAME = os.environ.get("FITBIT_CLIENT_SECRET_SECRET_NAME")
GOOGLE_TOKEN_PATH = Path(
    os.environ.get("GOOGLE_TOKEN_PATH", "/tmp/credentials/google_token.json")
)
FITBIT_TOKEN_PATH = Path(
    os.environ.get("FITBIT_TOKEN_PATH", "/tmp/credentials/fitbit_token.json")
)
LAMBDA_TASK_ROOT = Path(os.environ.get("LAMBDA_TASK_ROOT", ""))


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
    if not secret_name:
        raise ValueError("Secret name cannot be empty")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise ValueError(f"Failed to retrieve secret {secret_name}") from e

    return get_secret_value_response["SecretString"]


def update_secret(secret_name: str, secret_value: str) -> None:
    """
    Update a secret in AWS Secrets Manager
    """
    if not secret_name:
        raise ValueError("Secret name cannot be empty")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        client.update_secret(SecretId=secret_name, SecretString=secret_value)
        logger.info(f"Successfully updated secret {secret_name}")
    except ClientError as e:
        raise ValueError(f"Failed to update secret {secret_name}") from e


def setup_oauth_tokens() -> None:
    """
    Set up OAuth tokens from AWS Secrets Manager
    """
    if not GOOGLE_TOKEN_SECRET_NAME:
        raise ValueError("GOOGLE_TOKEN_SECRET_NAME environment variable not set")
    if not FITBIT_TOKEN_SECRET_NAME:
        raise ValueError("FITBIT_TOKEN_SECRET_NAME environment variable not set")
    if not FITBIT_CLIENT_ID_SECRET_NAME:
        raise ValueError("FITBIT_CLIENT_ID_SECRET_NAME environment variable not set")
    if not FITBIT_CLIENT_SECRET_SECRET_NAME:
        raise ValueError(
            "FITBIT_CLIENT_SECRET_SECRET_NAME environment variable not set"
        )

    # Make sure the directory exists
    GOOGLE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Retrieve and save Google token
    logger.info(f"Retrieving Google token from {GOOGLE_TOKEN_SECRET_NAME}")
    google_token = get_secret(GOOGLE_TOKEN_SECRET_NAME)
    GOOGLE_TOKEN_PATH.write_text(google_token)
    logger.info(f"Saved Google token to {GOOGLE_TOKEN_PATH}")

    # Retrieve and save Fitbit token
    logger.info(f"Retrieving Fitbit token from {FITBIT_TOKEN_SECRET_NAME}")
    fitbit_token = get_secret(FITBIT_TOKEN_SECRET_NAME)
    FITBIT_TOKEN_PATH.write_text(fitbit_token)
    logger.info(f"Saved Fitbit token to {FITBIT_TOKEN_PATH}")

    # Retrieve and set Fitbit client ID and secret as environment variables
    logger.info(f"Retrieving Fitbit client ID from {FITBIT_CLIENT_ID_SECRET_NAME}")
    fitbit_client_id = get_secret(FITBIT_CLIENT_ID_SECRET_NAME)
    os.environ["FITBIT_CLIENT_ID"] = fitbit_client_id
    logger.info("Set FITBIT_CLIENT_ID environment variable")

    logger.info(
        f"Retrieving Fitbit client secret from {FITBIT_CLIENT_SECRET_SECRET_NAME}"
    )
    fitbit_client_secret = get_secret(FITBIT_CLIENT_SECRET_SECRET_NAME)
    os.environ["FITBIT_CLIENT_SECRET"] = fitbit_client_secret
    logger.info("Set FITBIT_CLIENT_SECRET environment variable")


def upload_refreshed_fitbit_tokens() -> None:
    """
    Upload refreshed Fitbit tokens back to AWS Secrets Manager
    """
    if not FITBIT_TOKEN_SECRET_NAME:
        logger.warning("FITBIT_TOKEN_SECRET_NAME not set, skipping token upload")
        return

    # Check if the token file exists and has been updated
    if not FITBIT_TOKEN_PATH.exists():
        logger.warning(f"Fitbit token file not found at {FITBIT_TOKEN_PATH}")
        return

    try:
        # Read the updated token file
        updated_token_content = FITBIT_TOKEN_PATH.read_text()

        # Upload the updated token to Secrets Manager
        logger.info(f"Uploading refreshed Fitbit tokens to {FITBIT_TOKEN_SECRET_NAME}")
        update_secret(FITBIT_TOKEN_SECRET_NAME, updated_token_content)

    except Exception as e:
        logger.error(f"Failed to upload refreshed Fitbit tokens: {e}")
        # Don't raise the exception as this shouldn't fail the main sync operation


def handler(event: Dict[str, Any], _context: AWSContext) -> Dict[str, Any]:
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
        script_path = str(LAMBDA_TASK_ROOT / "bin" / "fitbit-sheets-sync.py")

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

        # Stream output line by line
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
        ) as process:
            if process.stdout:
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        logger.info(line)

            return_code = process.wait(timeout=30)
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, cmd)

        # Log result
        logger.info("Sync completed successfully")

        # Upload any refreshed Fitbit tokens back to Secrets Manager
        upload_refreshed_fitbit_tokens()

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

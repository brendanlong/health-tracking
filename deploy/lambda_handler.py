import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, TypedDict, cast


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


def get_secret() -> str:
    """
    Retrieve Google API credentials from AWS Secrets Manager
    """
    # boto3 and botocore will be available in the Lambda environment
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore

    secret_name = os.environ.get("GOOGLE_CREDENTIALS_SECRET_NAME")
    if not secret_name:
        raise ValueError("GOOGLE_CREDENTIALS_SECRET_NAME environment variable not set")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise e

    return get_secret_value_response["SecretString"]


def handler(event: Dict[str, Any], context: AWSContext) -> Dict[str, Any]:
    """
    Lambda handler function
    """
    logger.info("Starting health data sync")
    credentials_path: Optional[str] = None

    try:
        # Get configuration from environment or event
        sync_type = os.environ.get("SYNC_TYPE") or event.get("sync_type")
        spreadsheet_id = os.environ.get("SPREADSHEET_ID") or event.get("spreadsheet_id")
        sheet_name = os.environ.get("SHEET_NAME") or event.get("sheet_name")

        if not all([sync_type, spreadsheet_id, sheet_name]):
            raise ValueError(
                "Missing required parameters: sync_type, spreadsheet_id, sheet_name"
            )

        # Get Google credentials from Secrets Manager and save to a temporary file
        google_credentials = get_secret()
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=True
        ) as temp_file:
            temp_file.write(google_credentials)
            credentials_path = temp_file.name

            # Set environment variable for Google credentials
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

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
            ]

            # Execute sync script
            logger.info(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

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

#!/bin/bash
set -euo pipefail

# Configuration - modify these variables as needed
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPOSITORY_NAME="health-tracking"
ECR_STACK_NAME="health-tracking-ecr"
LAMBDA_STACK_NAME="health-tracking-lambda"
GOOGLE_CREDENTIALS_SECRET_NAME="health-tracking/google-credentials"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

# Display script usage
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --spreadsheet-id <id>     (required) Google Sheets spreadsheet ID"
  echo "  --sleep-sheet <name>      (optional) Name of the sheet for sleep data (default: Sleep)"
  echo "  --heartrate-sheet <name>  (optional) Name of the sheet for heart rate data (default: HeartRate)"
  echo "  --google-creds <path>     (required) Path to Google service account credentials JSON file"
  echo "  --region <region>         (optional) AWS region (default: $AWS_REGION)"
  echo "  --help                    Display this help message"
  exit 1
}

# Parse command line arguments
SPREADSHEET_ID=""
SLEEP_SHEET_NAME="Sleep"
HEARTRATE_SHEET_NAME="HeartRate"
GOOGLE_CREDS_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --spreadsheet-id)
      SPREADSHEET_ID="$2"
      shift 2
      ;;
    --sleep-sheet)
      SLEEP_SHEET_NAME="$2"
      shift 2
      ;;
    --heartrate-sheet)
      HEARTRATE_SHEET_NAME="$2"
      shift 2
      ;;
    --google-creds)
      GOOGLE_CREDS_PATH="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Validate required parameters
if [ -z "$SPREADSHEET_ID" ]; then
  echo "Error: --spreadsheet-id is required"
  usage
fi

if [ -z "$GOOGLE_CREDS_PATH" ]; then
  echo "Error: --google-creds is required"
  usage
fi

if [ ! -f "$GOOGLE_CREDS_PATH" ]; then
  echo "Error: Google credentials file not found at $GOOGLE_CREDS_PATH"
  exit 1
fi

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "Error: AWS CLI is not installed. Please install it before running this script."
  exit 1
fi

# Ensure Docker is installed
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed. Please install it before running this script."
  exit 1
fi

# Step 1: Deploy ECR stack first
echo "Deploying ECR CloudFormation stack..."
aws cloudformation deploy \
  --template-file ecr-stack.yaml \
  --stack-name "$ECR_STACK_NAME" \
  --parameter-overrides \
    ECRRepositoryName="$ECR_REPOSITORY_NAME" \
  --region "$AWS_REGION"

# Step 2: Get the ECR repository URI from CloudFormation outputs
echo "Getting ECR repository URI from CloudFormation stack..."
ECR_REPOSITORY_URI=$(aws cloudformation describe-stacks \
  --stack-name "$ECR_STACK_NAME" \
  --region "$AWS_REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryURI'].OutputValue" \
  --output text)

if [ -z "$ECR_REPOSITORY_URI" ]; then
  echo "Error: Failed to get ECR repository URI from CloudFormation stack"
  exit 1
fi

echo "Using ECR repository: $ECR_REPOSITORY_URI"

# Step 3: Build and push Docker image to ECR
echo "Building and pushing Docker image to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REPOSITORY_URI"

# Change directory to script location to ensure Dockerfile is found
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

(cd .. && docker build -f deploy/Dockerfile -t "$ECR_REPOSITORY_URI:$IMAGE_TAG" .)
docker push "$ECR_REPOSITORY_URI:$IMAGE_TAG"

echo "Docker image pushed successfully: $ECR_REPOSITORY_URI:$IMAGE_TAG"

# Step 4: Deploy Lambda stack (this will create the empty secret)
echo "Deploying Lambda CloudFormation stack..."
aws cloudformation deploy \
  --template-file lambda-stack.yaml \
  --stack-name "$LAMBDA_STACK_NAME" \
  --parameter-overrides \
    GoogleCredentialsSecretName="$GOOGLE_CREDENTIALS_SECRET_NAME" \
    ECRRepositoryUri="$ECR_REPOSITORY_URI" \
    ImageTag="$IMAGE_TAG" \
    SpreadsheetId="$SPREADSHEET_ID" \
    SleepSheetName="$SLEEP_SHEET_NAME" \
    HeartRateSheetName="$HEARTRATE_SHEET_NAME" \
  --capabilities CAPABILITY_IAM \
  --region "$AWS_REGION"

# Step 5: Update the secret with the actual Google credentials
echo "Updating Google credentials in AWS Secrets Manager..."
aws secretsmanager update-secret \
  --secret-id "$GOOGLE_CREDENTIALS_SECRET_NAME" \
  --secret-string file://"$GOOGLE_CREDS_PATH" \
  --region "$AWS_REGION"

echo "Deployment completed successfully!"
echo "Lambda stack name: $LAMBDA_STACK_NAME"
echo "ECR stack name: $ECR_STACK_NAME"
echo "Lambda functions deployed:"
echo "  - health-tracking-sleep-sync"
echo "  - health-tracking-heartrate-sync"
echo "Configured to run daily and sync data to spreadsheet ID: $SPREADSHEET_ID"
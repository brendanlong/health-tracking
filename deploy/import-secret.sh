#!/bin/bash
set -euo pipefail

# Configuration
AWS_REGION=${AWS_REGION:-"us-east-1"}
LAMBDA_STACK_NAME="health-tracking-lambda"
GOOGLE_CREDENTIALS_SECRET_NAME="health-tracking/google-credentials"

# Ensure AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "Error: AWS CLI is not installed. Please install it before running this script."
  exit 1
fi

# Get ARN of the existing secret
echo "Getting ARN for secret $GOOGLE_CREDENTIALS_SECRET_NAME..."
SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id "$GOOGLE_CREDENTIALS_SECRET_NAME" \
  --region "$AWS_REGION" \
  --query "ARN" \
  --output text)

if [ -z "$SECRET_ARN" ]; then
  echo "Error: Failed to get ARN for secret $GOOGLE_CREDENTIALS_SECRET_NAME"
  exit 1
fi

echo "Secret ARN: $SECRET_ARN"

# Generate a CloudFormation template with just the secret for import
echo "Generating import template..."
cat > secret-import-template.yaml << EOF
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Import template for existing Secret'

Resources:
  GoogleCredentialsSecret:
    Type: AWS::SecretsManager::Secret
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      Name: ${GOOGLE_CREDENTIALS_SECRET_NAME}
      Description: "Google API credentials for health tracking sync"
EOF

# Create a change set for import
echo "Creating import change set..."
CHANGE_SET_NAME="ImportSecret-$(date +%s)"

aws cloudformation create-change-set \
  --stack-name "$LAMBDA_STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --change-set-type IMPORT \
  --resources-to-import "[{\"ResourceType\":\"AWS::SecretsManager::Secret\",\"LogicalResourceId\":\"GoogleCredentialsSecret\",\"ResourceIdentifier\":{\"Id\":\"$SECRET_ARN\"}}]" \
  --template-body file://secret-import-template.yaml \
  --region "$AWS_REGION"

echo "Waiting for change set creation..."
aws cloudformation wait change-set-create-complete \
  --stack-name "$LAMBDA_STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --region "$AWS_REGION"

# Execute the change set to import the secret
echo "Executing change set to import the secret..."
aws cloudformation execute-change-set \
  --stack-name "$LAMBDA_STACK_NAME" \
  --change-set-name "$CHANGE_SET_NAME" \
  --region "$AWS_REGION"

echo "Waiting for change set execution to complete..."
aws cloudformation wait stack-import-complete \
  --stack-name "$LAMBDA_STACK_NAME" \
  --region "$AWS_REGION"

echo "Secret successfully imported into CloudFormation stack!"
echo "You can now deploy the full Lambda stack which will use this imported secret."
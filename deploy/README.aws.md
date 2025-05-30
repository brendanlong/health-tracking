# AWS Lambda Deployment for Health Tracking

This guide explains how to deploy the health tracking sync tools to AWS Lambda using Docker and CloudFormation. The setup allows you to automatically sync your Fitbit data to Google Sheets on a daily schedule.

## Prerequisites

1. AWS CLI installed and configured with appropriate permissions
2. Docker installed locally
3. OAuth tokens for Google and Fitbit (JSON files)
4. A Google Sheet to store your health data
5. Fitbit API client ID and secret

## Components

The deployment creates the following AWS resources across two CloudFormation stacks:

**ECR Stack:**
- Amazon ECR repository for the Docker image

**Lambda Stack:**
- Two Lambda functions (for sleep and heart rate data)
- CloudWatch Event rules for daily scheduling
- IAM roles with necessary permissions
- AWS Secrets Manager secrets for storing OAuth tokens

## Deployment Instructions

### 1. Prepare for Deployment

Make sure you have:
- Your Google Sheets spreadsheet ID
- Names of the sheets for sleep and heart rate data
- Path to your Google OAuth token file (credentials/google_token.json)
- Path to your Fitbit OAuth token file (credentials/fitbit_token.json)

### 2. Deploy the Application

Run the deployment script with your configuration:

```bash
cd deploy
./deploy.sh \
  --spreadsheet-id YOUR_SPREADSHEET_ID \
  --sleep-sheet "Sleep" \
  --heartrate-sheet "HeartRate" \
  --google-token path/to/google_token.json \
  --fitbit-token path/to/fitbit_token.json \
  --fitbit-client-id YOUR_FITBIT_CLIENT_ID \
  --fitbit-client-secret YOUR_FITBIT_CLIENT_SECRET
```

The script will:
1. Deploy the ECR CloudFormation stack to create the ECR repository
2. Build and push the Docker image to the ECR repository
3. Deploy the Lambda CloudFormation stack with the Lambda functions and other resources
4. Upload both Google and Fitbit OAuth tokens to AWS Secrets Manager

### 3. Verify Deployment

After deployment completes:

1. Go to the AWS Lambda console to verify both functions were created
2. Check the CloudWatch Events rules to ensure they're scheduled correctly
3. You can manually invoke the Lambda functions to test them

### 4. Monitoring

All Lambda function output is sent to CloudWatch Logs. To view logs:

1. Go to the CloudWatch Logs console
2. Select the log group for either Lambda function (/aws/lambda/health-tracking-sleep-sync or /aws/lambda/health-tracking-heartrate-sync)
3. Review the logs for any errors or issues

## Troubleshooting

### Common Issues

1. **Missing Google Permissions**: Ensure your Google service account has access to the spreadsheet
2. **Lambda Timeout**: If syncs are failing due to timeout, increase the timeout value in the CloudFormation template
3. **ECR Authentication Failure**: Run `aws ecr get-login-password` manually to verify authentication

### Making Changes

To update your deployment:

1. Make changes to the code or configuration
2. Run the deploy script again with the same parameters
3. The script will update both stacks as needed

## Testing

### Manual Testing in AWS

To manually invoke the Lambda functions in AWS:

```bash
aws lambda invoke \
  --function-name health-tracking-sleep-sync \
  --payload '{}' \
  response.json

aws lambda invoke \
  --function-name health-tracking-heartrate-sync \
  --payload '{}' \
  response.json
```

Check response.json and the CloudWatch Logs for results.

### Local Testing with Docker

To test the Lambda function locally before deploying to AWS:

1. Build the Docker image:
   ```bash
   cd /path/to/health-tracking
   docker build -f deploy/Dockerfile -t health-tracking-local .
   ```

2. Run the container with the Lambda Runtime Interface Emulator:
   ```bash
   docker run --rm -it \
     -e SYNC_TYPE=sleep \
     -e SPREADSHEET_ID=your-spreadsheet-id \
     -e SHEET_NAME=Sleep \
     -e GOOGLE_TOKEN_SECRET_NAME=health-tracking/google-token \
     -e FITBIT_TOKEN_SECRET_NAME=health-tracking/fitbit-token \
     -e FITBIT_CLIENT_ID=your-fitbit-client-id \
     -e FITBIT_CLIENT_SECRET=your-fitbit-client-secret \
     -e AWS_REGION=us-east-1 \
     -p 9000:8080 \
     health-tracking-local
   ```

3. In another terminal, invoke the function with curl:
   ```bash
   curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
   ```

   You can also provide custom parameters:
   ```bash
   curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{
     "sync_type": "heart-rate",
     "spreadsheet_id": "your-spreadsheet-id",
     "sheet_name": "CustomSheetName"
   }'
   ```

Note: For local testing, you'll need to have the AWS credentials configured that have access to the Secrets Manager secrets, or you can mount your token files directly as volumes.
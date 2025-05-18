# AWS Lambda Deployment Plan

## Infrastructure Components
- [x] AWS Lambda Function (containerized)
- [x] Amazon EventBridge (CloudWatch Events) for scheduling
- [x] AWS Secrets Manager for Google API credentials
- [x] IAM Roles and Permissions
- [x] CloudFormation template (split into ECR and Lambda stacks)

## Development Tasks

### 1. Docker Setup
- [x] Create Dockerfile based on AWS Lambda Python base image
- [x] Set up proper dependencies and entry point
- [ ] Test container locally with AWS Lambda Runtime Interface Emulator

### 2. Credentials Management
- [x] Set up AWS Secrets Manager for Google credentials
- [x] Create code to retrieve and use credentials at runtime
- [x] Update Lambda to reference existing secret

### 3. Lambda Function
- [x] Create Lambda handler function
- [x] Modify code to accept parameters via environment variables
- [x] Add logging for CloudWatch
- [ ] Test with simulated AWS Lambda environment

### 4. CloudFormation
- [x] Create template for Lambda function
- [x] Create separate template for ECR repository
- [x] Set up EventBridge rule for daily scheduling
- [x] Configure IAM roles with least privilege

### 5. Deployment
- [x] Create deployment script for Docker image to Amazon ECR
- [x] Create deployment script for CloudFormation stack
- [x] Update deployment script to deploy two stacks sequentially
- [ ] Verify deployment and execution
- [ ] Test complete workflow

### 6. Monitoring and Maintenance
- [ ] Set up CloudWatch alarms for failures
- [x] Create documentation for deployment process
- [ ] Create documentation for maintaining the deployment

## Next Steps

1. Test the deployment process:
   ```
   cd deploy
   ./deploy.sh --spreadsheet-id YOUR_SPREADSHEET_ID --google-creds path/to/credentials.json
   ```

2. Verify the Lambda functions are executing correctly by checking CloudWatch logs

3. Set up CloudWatch alarms for Lambda function failures (optional)
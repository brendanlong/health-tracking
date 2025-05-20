FROM public.ecr.aws/lambda/python:3.12

# Required Environment Variables:
# GOOGLE_TOKEN_SECRET_NAME - AWS Secrets Manager secret name containing Google OAuth tokens
# FITBIT_TOKEN_SECRET_NAME - AWS Secrets Manager secret name containing Fitbit OAuth tokens
# SYNC_TYPE - Type of data to sync (e.g., "sleep" or "heart-rate")
# SPREADSHEET_ID - Google Sheets spreadsheet ID to write to
# SHEET_NAME - Name of the specific sheet to write to
#
# Required for Fitbit authentication:
# FITBIT_CLIENT_ID - Fitbit API client ID
# FITBIT_CLIENT_SECRET - Fitbit API client secret

ENV GOOGLE_TOKEN_PATH=/tmp/credentials/google_token.json
ENV FITBIT_TOKEN_PATH=/tmp/credentials/fitbit_token.json

# Create a directory for temporary credential files
RUN mkdir -p /tmp/credentials

WORKDIR ${LAMBDA_TASK_ROOT}

# Add uv's venv site-packages and our app to the Python path
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/.venv/lib/python3.12/site-packages:${LAMBDA_TASK_ROOT}/src:${PYTHONPATH}"

# Copy requirements first for better layer caching
COPY pyproject.toml uv.lock ./
RUN pip install uv
RUN uv sync --no-install-project --locked

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY bin/ ${LAMBDA_TASK_ROOT}/bin/

RUN uv sync --locked

# Lambda handler function
COPY deploy/lambda_handler.py ${LAMBDA_TASK_ROOT}

CMD [ "lambda_handler.handler" ]
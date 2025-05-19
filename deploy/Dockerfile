FROM public.ecr.aws/lambda/python:3.12

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
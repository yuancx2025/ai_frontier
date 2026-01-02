# FROM python:3.11-slim

# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     gcc \
#     postgresql-client \
#     && rm -rf /var/lib/apt/lists/*

# COPY pyproject.toml uv.lock ./

# RUN uv pip install --system -r pyproject.toml

# COPY . .

# # Support both local development and Lambda execution
# # 
# # LOCAL DEVELOPMENT:
# #   docker run --env-file .env <image> 
# #   or: docker run -e DATABASE_URL=... -e GEMINI_API_KEY=... <image>
# #   Runs: CMD ["uv", "run", "main.py"]
# #
# # LAMBDA EXECUTION:
# #   Configure handler in AWS Lambda console/CLI:
# #   Handler: lambda_handlers.scrape_handler.lambda_handler
# #   Lambda runtime will call the handler function directly, ignoring CMD
# #   Handlers retrieve secrets from AWS Secrets Manager and set env vars
# CMD ["uv", "run", "main.py"]

# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies (gcc-c++ for numpy, postgresql-devel for psycopg2)
RUN yum install -y gcc gcc-c++ postgresql postgresql-devel && yum clean all

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Set Lambda handler entry point
# Lambda will call lambda_handler() in this file
# The actual handler is selected via LAMBDA_HANDLER env var
CMD ["lambda_handlers.entrypoint.lambda_handler"]
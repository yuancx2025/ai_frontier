FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv pip install --system -r pyproject.toml

COPY . .

# Support both local development and Lambda execution
# 
# LOCAL DEVELOPMENT:
#   docker run --env-file .env <image> 
#   or: docker run -e DATABASE_URL=... -e GEMINI_API_KEY=... <image>
#   Runs: CMD ["uv", "run", "main.py"]
#
# LAMBDA EXECUTION:
#   Configure handler in AWS Lambda console/CLI:
#   Handler: lambda_handlers.scrape_handler.lambda_handler
#   Lambda runtime will call the handler function directly, ignoring CMD
#   Handlers retrieve secrets from AWS Secrets Manager and set env vars
CMD ["uv", "run", "main.py"]


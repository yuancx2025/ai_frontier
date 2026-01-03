# Use standard Python base image for Fargate (not Lambda)
FROM python:3.11-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY . .

# Fargate will run this command
# Can be overridden in ECS task definition if needed
CMD ["uv", "run", "python", "main.py"]

# Deployment Directory

This directory contains all deployment-related files and documentation for the AI News Aggregator project.

## Structure

```
deployment/
├── README.md                      # This file
├── AWS_DEPLOYMENT.md              # AWS deployment guide
├── GCP_DEPLOYMENT.md              # Google Cloud deployment guide
├── GENERAL_CLOUD_DEPLOYMENT.md    # General cloud deployment guide
├── docker-compose.yml             # Local development with Docker Compose
```

## Files Overview

### Docker Compose (`docker-compose.yml`)

**Purpose**: Local development only

Docker Compose is used for **local development** to run both the application and PostgreSQL database together. It's **NOT needed** for cloud deployments because:

- Cloud providers manage databases separately (RDS, Cloud SQL, etc.)
- Containers are deployed individually, not as a compose stack
- Cloud platforms handle orchestration (ECS, Cloud Run, etc.)

**When to use:**
- ✅ Local development and testing
- ✅ Running the full stack on your machine
- ❌ NOT for cloud deployments

**Usage:**
```bash
cd deployment
docker-compose up -d
```

### Dockerfile

**Location**: `deployment/Dockerfile`

**Purpose**: Required for ALL deployments (local and cloud)

The Dockerfile defines how to build your container image. It's needed for:
- Local Docker builds
- Cloud Build (GCP)
- CodeBuild (AWS)
- Any container registry

**Usage:**
```bash
# Build from project root
docker build -f deployment/Dockerfile -t ai-frontier .

# Or from deployment directory
cd deployment
docker build -f Dockerfile -t ai-frontier ..
```

### Cloud Build Files

#### `cloudbuild.yaml` (Google Cloud Platform)

**Location**: Root directory (`/cloudbuild.yaml`)

**Purpose**: Automated Docker image builds on GCP

When you push code to a Git repository, Cloud Build automatically:
1. Builds your Docker image using the Dockerfile
2. Pushes it to Artifact Registry
3. Can trigger Cloud Run deployments

**Usage:**
```bash
# From project root
gcloud builds submit --config cloudbuild.yaml
```

**Note**: The Dockerfile path in cloudbuild.yaml points to `deployment/Dockerfile`. The cloudbuild.yaml file is at the project root.

#### `buildspec.yml` (AWS CodeBuild)

**Location**: Root directory (`/buildspec.yml`)

**Purpose**: Automated Docker image builds on AWS

AWS CodeBuild uses this file to:
1. Build your Docker image
2. Push it to ECR (Elastic Container Registry)
3. Can trigger ECS deployments

**Usage:**
- Create a CodeBuild project in AWS Console
- Point it to your Git repository
- CodeBuild automatically uses `buildspec.yml` from the root directory

**Alternative**: You can also build locally and push to ECR:
```bash
docker build -f deployment/Dockerfile -t ai-frontier .
docker tag ai-frontier:latest <ecr-repo>:latest
docker push <ecr-repo>:latest
```

## Cloud Deployment Comparison

### Google Cloud Platform (GCP)

**Required Files:**
- ✅ `deployment/Dockerfile`
- ✅ `cloudbuild.yaml` (at root, for automated builds)
- ❌ `docker-compose.yml` (not needed)

**Build Options:**
1. **Automated**: Push to Git → Cloud Build automatically builds using `cloudbuild.yaml`
2. **Manual**: `gcloud builds submit --config cloudbuild.yaml`
3. **Local**: Build locally, push to Artifact Registry

### AWS

**Required Files:**
- ✅ `deployment/Dockerfile`
- ✅ `buildspec.yml` (at root, for CodeBuild - optional)
- ❌ `docker-compose.yml` (not needed)

**Build Options:**
1. **CodeBuild**: Use `buildspec.yml` (at root) for automated builds
2. **Manual**: Build locally, push to ECR
3. **ECR Build**: Use ECR's build capabilities

**Note**: AWS doesn't require a buildspec.yml if you build locally. You can:
```bash
# Build locally
docker build -f deployment/Dockerfile -t ai-frontier .

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker tag ai-frontier:latest <ecr-repo>:latest
docker push <ecr-repo>:latest
```

### Other Cloud Providers

Most cloud providers follow similar patterns:
- ✅ `Dockerfile` required
- ✅ Provider-specific build config (optional, for CI/CD)
- ❌ `docker-compose.yml` not needed for cloud deployments

## Quick Reference

| File | Purpose | Cloud Needed? | Local Needed? |
|------|---------|---------------|---------------|
| `deployment/Dockerfile` | Build container image | ✅ Yes | ✅ Yes |
| `deployment/docker-compose.yml` | Local dev stack | ❌ No | ✅ Yes |
| `cloudbuild.yaml` (root) | GCP automated builds | ✅ Optional | ❌ No |
| `buildspec.yml` (root) | AWS CodeBuild | ✅ Optional | ❌ No |

## Summary

**For Cloud Deployments:**
- ✅ Always need: `deployment/Dockerfile`
- ✅ Optional: Provider-specific build configs (`cloudbuild.yaml` and `buildspec.yml` at root)
- ❌ Don't need: `docker-compose.yml`

**For Local Development:**
- ✅ Need: `deployment/Dockerfile` and `docker-compose.yml`

The `docker-compose.yml` file is purely for local development convenience - it lets you run PostgreSQL and your app together with one command. In the cloud, these services are managed separately by your cloud provider.

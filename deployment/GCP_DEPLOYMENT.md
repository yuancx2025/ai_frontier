# Google Cloud Deployment Guide: Cloud Run + Cloud SQL

This guide walks you through deploying the AI News Aggregator to Google Cloud Platform using:
- **Cloud Run**: Serverless container execution
- **Cloud SQL**: Managed PostgreSQL database
- **Cloud Scheduler**: Scheduled daily execution
- **Cloud Build**: Automated Docker image builds
- **Artifact Registry**: Docker image storage
- **Secret Manager**: Secure credential storage

## Architecture Overview

```
Cloud Scheduler (Cron Schedule)
    ↓ triggers daily
Cloud Run (Containerized Job)
    ↓ connects via Unix socket
Cloud SQL PostgreSQL
    ↓ uses
Artifact Registry (Docker Images)
    ↓ stores secrets in
Secret Manager
```

## Prerequisites

- Google Cloud Account
- Google Cloud SDK (`gcloud`) installed and configured
- Docker installed locally (optional, Cloud Build can build for you)
- Billing enabled on GCP project

## Step-by-Step Deployment

### Step 1: Set Up GCP Project and Enable APIs

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

### Step 2: Create Cloud SQL PostgreSQL Instance

```bash
# Create Cloud SQL instance
gcloud sql instances create ai-news-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=YourSecurePassword123! \
  --storage-type=SSD \
  --storage-size=10GB \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --authorized-networks=0.0.0.0/0 \
  --database-flags=max_connections=100

# Wait for instance to be ready (takes 5-10 minutes)
gcloud sql instances describe ai-news-db

# Create database
gcloud sql databases create ai_news_aggregator \
  --instance=ai-news-db

# Create user (optional, can use default postgres user)
gcloud sql users create app_user \
  --instance=ai-news-db \
  --password=YourUserPassword123!

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe ai-news-db \
  --format="value(connectionName)")

echo "Connection name: $CONNECTION_NAME"
```

**Note**: For production, consider:
- Using a larger instance (db-n1-standard-1 or higher)
- Enabling high availability
- Using private IP only
- Restricting authorized networks

### Step 3: Store Secrets in Secret Manager

```bash
# Store Gemini API key
echo -n "your_gemini_api_key_here" | \
  gcloud secrets create gemini-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Store email
echo -n "your_email@gmail.com" | \
  gcloud secrets create my-email \
  --data-file=- \
  --replication-policy="automatic"

# Store app password
echo -n "your_gmail_app_password" | \
  gcloud secrets create app-password \
  --data-file=- \
  --replication-policy="automatic"

# Store database password
echo -n "YourSecurePassword123!" | \
  gcloud secrets create db-password \
  --data-file=- \
  --replication-policy="automatic"
```

### Step 4: Create Service Account for Cloud Run

```bash
# Create service account
gcloud iam service-accounts create ai-news-service \
  --display-name="AI News Aggregator Service Account" \
  --description="Service account for AI News Aggregator Cloud Run service"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ai-news-service@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant Cloud SQL Client access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ai-news-service@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Step 5: Create Artifact Registry Repository

```bash
# Create repository for Docker images
gcloud artifacts repositories create ai-frontier \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker images for AI News Aggregator"

# Configure Docker authentication
gcloud auth configure-docker $REGION-docker.pkg.dev
```

### Step 6: Build and Push Docker Image

**Option A: Using Cloud Build (Recommended)**

The `cloudbuild.yaml` file is at the project root. Here's what it contains:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - '$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:$SHORT_SHA'
      - '-t'
      - '$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest'
      - '.'

  # Push the container image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier'

images:
  - '$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:$SHORT_SHA'
  - '$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest'
```

Build and push:

```bash
# Submit build to Cloud Build (run from project root)
gcloud builds submit --config cloudbuild.yaml

# Get image URL
IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest"
```

**Option B: Local Build and Push**

```bash
# Build locally
docker build -f deployment/Dockerfile -t ai-frontier .

# Tag for Artifact Registry
docker tag ai-frontier:latest \
  $REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest

# Push to Artifact Registry
docker push $REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/ai-frontier/ai-frontier:latest"
```

### Step 7: Deploy to Cloud Run

```bash
# Deploy Cloud Run service
gcloud run deploy ai-frontier \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=ai-news-service@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --set-env-vars="ENVIRONMENT=PRODUCTION" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,MY_EMAIL=my-email:latest,APP_PASSWORD=app-password:latest,DB_PASSWORD=db-password:latest" \
  --memory=1Gi \
  --cpu=1 \
  --timeout=3600 \
  --max-instances=1 \
  --min-instances=0 \
  --concurrency=1

# Get service URL
SERVICE_URL=$(gcloud run services describe ai-frontier \
  --region=$REGION \
  --format="value(status.url)")

echo "Service URL: $SERVICE_URL"
```

**Important**: For Cloud SQL connection, you need to construct the DATABASE_URL using the Unix socket path. Update the deployment with the database URL:

```bash
# Construct database URL using Unix socket
DB_URL="postgresql://postgres:$(gcloud secrets versions access latest --secret=db-password)@/ai_news_aggregator?host=/cloudsql/$CONNECTION_NAME"

# Store database URL as secret
echo -n "$DB_URL" | \
  gcloud secrets create database-url \
  --data-file=- \
  --replication-policy="automatic"

# Update Cloud Run service with database URL
gcloud run services update ai-frontier \
  --region=$REGION \
  --update-secrets="DATABASE_URL=database-url:latest"
```

### Step 8: Create Cloud Scheduler Job

```bash
# Create service account for Cloud Scheduler
gcloud iam service-accounts create cloud-scheduler-sa \
  --display-name="Cloud Scheduler Service Account"

# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding ai-frontier \
  --region=$REGION \
  --member="serviceAccount:cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create scheduled job (5 AM UTC daily)
gcloud scheduler jobs create http daily-digest-job \
  --location=$REGION \
  --schedule="0 5 * * *" \
  --uri="$SERVICE_URL" \
  --http-method=GET \
  --oidc-service-account-email=cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --time-zone="UTC" \
  --description="Daily AI News Aggregator execution"
```

### Step 9: Initialize Database Tables

Run a one-time Cloud Run job to initialize the database:

```bash
# Create a job for database initialization
gcloud run jobs create init-database \
  --image=$IMAGE_URL \
  --region=$REGION \
  --service-account=ai-news-service@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --set-env-vars="ENVIRONMENT=PRODUCTION" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=1 \
  --command="uv,run,python,-m,app.database.create_tables"

# Execute the job
gcloud run jobs execute init-database --region=$REGION

# Wait for completion and check logs
gcloud run jobs executions list --job=init-database --region=$REGION
```

## Monitoring and Logs

### View Logs

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-frontier" \
  --limit=50 \
  --format=json

# Or view in Google Cloud Console:
# Cloud Logging → Logs Explorer → Filter by service name
```

### Check Cloud Scheduler Status

```bash
# List scheduler jobs
gcloud scheduler jobs list --location=$REGION

# Describe job
gcloud scheduler jobs describe daily-digest-job --location=$REGION

# View job execution history
gcloud scheduler jobs describe daily-digest-job \
  --location=$REGION \
  --format="value(state)"
```

### Monitor Cloud Run Service

```bash
# Describe service
gcloud run services describe ai-frontier --region=$REGION

# View metrics in Console:
# Cloud Run → ai-frontier → Metrics tab
```

## Cost Estimation

**Monthly costs (approximate):**
- Cloud SQL PostgreSQL (db-f1-micro): ~$7-10/month
- Cloud Run (1GB RAM, 1 CPU, ~30 min/day): ~$0.50-2/month
- Cloud Build (builds): ~$0.10-0.50/month
- Artifact Registry (5GB storage): ~$0.10/month
- Secret Manager: Free (first 6 secrets)
- Cloud Scheduler: Free (first 3 jobs)
- Data transfer: ~$1-2/month

**Total: ~$9-15/month**

## Troubleshooting

### Service Fails to Start

1. Check Cloud Run logs:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-frontier" --limit=20
   ```
2. Verify secrets are accessible:
   ```bash
   gcloud secrets versions access latest --secret=gemini-api-key
   ```
3. Check service account permissions
4. Verify Cloud SQL connection name is correct

### Database Connection Issues

1. Verify Cloud SQL instance is running:
   ```bash
   gcloud sql instances describe ai-news-db
   ```
2. Check Cloud SQL connection is added to Cloud Run service
3. Verify database URL uses Unix socket format:
   ```
   postgresql://user:password@/database?host=/cloudsql/CONNECTION_NAME
   ```
4. Test connection manually:
   ```bash
   gcloud sql connect ai-news-db --user=postgres
   ```

### Cloud Scheduler Not Triggering

1. Check job is enabled:
   ```bash
   gcloud scheduler jobs describe daily-digest-job --location=$REGION
   ```
2. Verify OIDC service account has `run.invoker` role
3. Check Cloud Scheduler logs in Cloud Logging
4. Manually trigger job to test:
   ```bash
   gcloud scheduler jobs run daily-digest-job --location=$REGION
   ```

## Updating the Deployment

### Update Docker Image

```bash
# Rebuild and push (using Cloud Build, run from project root)
gcloud builds submit --config cloudbuild.yaml

# Or rebuild locally and push
docker build -f deployment/Dockerfile -t ai-frontier .
docker tag ai-frontier:latest $IMAGE_URL
docker push $IMAGE_URL

# Update Cloud Run service
gcloud run services update ai-frontier \
  --region=$REGION \
  --image=$IMAGE_URL
```

### Update Environment Variables

```bash
# Update secret
echo -n "new_value" | \
  gcloud secrets versions add gemini-api-key \
  --data-file=-

# Cloud Run will automatically use the latest version
# Or force update:
gcloud run services update ai-frontier \
  --region=$REGION \
  --update-secrets="GEMINI_API_KEY=gemini-api-key:latest"
```

### Update Schedule

```bash
# Update schedule (e.g., 8 AM UTC)
gcloud scheduler jobs update http daily-digest-job \
  --location=$REGION \
  --schedule="0 8 * * *"
```

## Cleanup

To remove all resources:

```bash
# Delete Cloud Scheduler job
gcloud scheduler jobs delete daily-digest-job --location=$REGION

# Delete Cloud Run service
gcloud run services delete ai-frontier --region=$REGION

# Delete Cloud Run job
gcloud run jobs delete init-database --region=$REGION

# Delete Cloud SQL instance
gcloud sql instances delete ai-news-db

# Delete secrets
gcloud secrets delete gemini-api-key
gcloud secrets delete my-email
gcloud secrets delete app-password
gcloud secrets delete db-password
gcloud secrets delete database-url

# Delete Artifact Registry repository
gcloud artifacts repositories delete ai-frontier \
  --location=$REGION

# Delete service accounts
gcloud iam service-accounts delete ai-news-service@$PROJECT_ID.iam.gserviceaccount.com
gcloud iam service-accounts delete cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com
```

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs/postgres)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

# General Cloud Deployment Guide

This guide provides a general framework for deploying the AI News Aggregator to any cloud platform. It covers the essential components and steps needed regardless of your cloud provider choice.

## Architecture Components

Regardless of the cloud provider, you'll need:

1. **Container Runtime**: To run Docker containers
2. **Database Service**: Managed PostgreSQL database
3. **Scheduler/Orchestrator**: To run the job on a schedule
4. **Container Registry**: To store Docker images
5. **Secrets Management**: To securely store credentials
6. **Networking**: To connect containers to the database

## Common Deployment Pattern

```
Scheduler/Orchestrator
    ↓ triggers daily
Container Runtime
    ↓ connects to
Managed PostgreSQL Database
    ↓ uses
Container Registry (Docker Images)
    ↓ stores secrets in
Secrets Management Service
```

## Step-by-Step Deployment Framework

### Step 1: Prepare Your Docker Image

The project includes a `Dockerfile`. Build and test locally first:

```bash
# Build Docker image
docker build -f deployment/Dockerfile -t ai-frontier .

# Test locally with environment variables
docker run --env-file .env ai-frontier
```

**Key Dockerfile Requirements:**
- Python 3.11+
- PostgreSQL client libraries
- All dependencies from `pyproject.toml`
- Entry point: `uv run main.py`

### Step 2: Set Up Database

**Requirements:**
- PostgreSQL 12+ (15 recommended)
- Database name: `ai_news_aggregator`
- User with read/write permissions
- Network access from your container runtime

**Common Cloud Database Services:**
- **AWS**: RDS PostgreSQL
- **GCP**: Cloud SQL PostgreSQL
- **Azure**: Azure Database for PostgreSQL
- **DigitalOcean**: Managed Databases
- **Heroku**: Heroku Postgres
- **Railway**: Railway PostgreSQL

**Connection String Format:**
```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

**Initialize Database Tables:**
```bash
# Run this once after database is created
uv run python -m app.database.create_tables
```

### Step 3: Store Secrets Securely

**Required Secrets:**
- `GEMINI_API_KEY`: Google Gemini API key
- `MY_EMAIL`: Email address for sending digests
- `APP_PASSWORD`: Gmail app password (for SMTP)
- `DATABASE_URL`: PostgreSQL connection string

**Common Secrets Management Services:**
- **AWS**: Secrets Manager
- **GCP**: Secret Manager
- **Azure**: Key Vault
- **HashiCorp**: Vault
- **General**: Environment variables (less secure, but simpler)

**Best Practices:**
- Never commit secrets to version control
- Use managed secrets services when available
- Rotate secrets regularly
- Use least-privilege access policies

### Step 4: Set Up Container Registry

**Common Container Registries:**
- **AWS**: Elastic Container Registry (ECR)
- **GCP**: Artifact Registry
- **Azure**: Container Registry (ACR)
- **Docker Hub**: Public/private repositories
- **GitHub**: GitHub Container Registry (ghcr.io)

**Push Your Image:**
```bash
# Tag your image
docker tag ai-frontier:latest REGISTRY_URL/ai-frontier:latest

# Push to registry
docker push REGISTRY_URL/ai-frontier:latest
```

### Step 5: Configure Container Runtime

**Common Container Runtimes:**
- **AWS**: ECS Fargate, EKS (Kubernetes)
- **GCP**: Cloud Run, GKE (Kubernetes)
- **Azure**: Container Instances, AKS (Kubernetes)
- **DigitalOcean**: App Platform, Kubernetes
- **Heroku**: Container Registry + Dynos
- **Railway**: Railway Containers

**Container Configuration:**
- **CPU**: 0.5-1 vCPU
- **Memory**: 512MB-1GB
- **Timeout**: 3600 seconds (1 hour)
- **Environment Variables**: Set `ENVIRONMENT=PRODUCTION`
- **Secrets**: Mount from secrets management service

**Example Environment Variables:**
```bash
ENVIRONMENT=PRODUCTION
DATABASE_URL=postgresql://user:pass@host:5432/db
GEMINI_API_KEY=your_key
MY_EMAIL=your_email@gmail.com
APP_PASSWORD=your_app_password
```

### Step 6: Set Up Scheduling

**Common Schedulers:**
- **AWS**: EventBridge (CloudWatch Events)
- **GCP**: Cloud Scheduler
- **Azure**: Logic Apps, Azure Functions Timer Trigger
- **Kubernetes**: CronJob
- **General**: Cron on VM, GitHub Actions scheduled workflows

**Schedule Format (Cron):**
```
# Daily at 5 AM UTC
0 5 * * *
```

**Trigger Methods:**
- **HTTP**: Send HTTP request to container endpoint
- **Direct Execution**: Run container directly via scheduler
- **Message Queue**: Publish message to queue (SQS, Pub/Sub, etc.)

### Step 7: Configure Networking

**Database Connectivity:**
- **Private Network**: Best for security (VPC, VNet, etc.)
- **Public Network**: Simpler but requires firewall rules
- **Unix Socket**: Fastest (GCP Cloud SQL supports this)

**Security Groups/Firewall Rules:**
- Allow container runtime to access database port (5432)
- Restrict database access to specific IPs/networks
- Use SSL/TLS for database connections

### Step 8: Set Up Monitoring and Logging

**Essential Monitoring:**
- Container execution logs
- Database connection status
- Job execution success/failure
- Error tracking and alerting

**Common Logging Services:**
- **AWS**: CloudWatch Logs
- **GCP**: Cloud Logging
- **Azure**: Application Insights
- **General**: ELK Stack, Loki, Datadog

**Key Metrics to Monitor:**
- Job execution time
- Number of articles scraped
- Number of digests created
- Email send success rate
- Database connection errors

## Provider-Specific Quick Reference

### AWS
- **Container**: ECS Fargate
- **Database**: RDS PostgreSQL
- **Scheduler**: EventBridge
- **Registry**: ECR
- **Secrets**: Secrets Manager
- **See**: `docs/AWS_DEPLOYMENT.md`

### Google Cloud Platform
- **Container**: Cloud Run
- **Database**: Cloud SQL PostgreSQL
- **Scheduler**: Cloud Scheduler
- **Registry**: Artifact Registry
- **Secrets**: Secret Manager
- **See**: `docs/GCP_DEPLOYMENT.md`

### Azure
- **Container**: Container Instances or AKS
- **Database**: Azure Database for PostgreSQL
- **Scheduler**: Logic Apps or Azure Functions
- **Registry**: Azure Container Registry
- **Secrets**: Key Vault

### DigitalOcean
- **Container**: App Platform or Kubernetes
- **Database**: Managed Databases
- **Scheduler**: App Platform cron jobs or Kubernetes CronJob
- **Registry**: Container Registry
- **Secrets**: App Platform environment variables

### Heroku
- **Container**: Container Registry + Dynos
- **Database**: Heroku Postgres
- **Scheduler**: Heroku Scheduler add-on
- **Registry**: Container Registry
- **Secrets**: Config vars

### Railway
- **Container**: Railway Containers
- **Database**: Railway PostgreSQL
- **Scheduler**: Railway Cron Jobs
- **Registry**: Railway (auto-builds from Git)
- **Secrets**: Environment variables

### Kubernetes (Any Provider)
- **Container**: Kubernetes Pods
- **Database**: Managed PostgreSQL or self-hosted
- **Scheduler**: CronJob resource
- **Registry**: Any container registry
- **Secrets**: Kubernetes Secrets

## Environment Configuration

### Production Environment Detection

The application automatically detects production environment when:
- `ENVIRONMENT=PRODUCTION` is set, OR
- Database URL contains cloud provider domains:
  - `amazonaws.com` (AWS)
  - `cloudsql` or `googleapis.com` (GCP)
  - `azure.com` (Azure)

### Required Environment Variables

```bash
# Environment
ENVIRONMENT=PRODUCTION

# Database
DATABASE_URL=postgresql://user:password@host:port/database

# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration
MY_EMAIL=your_email@gmail.com
APP_PASSWORD=your_gmail_app_password

# Optional: Webshare Proxy (for YouTube transcripts)
WEBSHARE_USERNAME=your_username
WEBSHARE_PASSWORD=your_password
```

## Database Initialization

After setting up your database, initialize tables:

```bash
# Option 1: Run as part of container startup (add to Dockerfile CMD)
uv run python -m app.database.create_tables && uv run main.py

# Option 2: Run as separate one-time job
uv run python -m app.database.create_tables

# Option 3: Run manually from local machine
export DATABASE_URL="your_production_database_url"
uv run python -m app.database.create_tables
```

## Testing Your Deployment

### 1. Test Database Connection

```bash
# Check connection
uv run python -m app.database.check_connection
```

### 2. Test Individual Components

```bash
# Test scraping
uv run python -m app.runner

# Test processing
uv run python -m app.services.process_anthropic
uv run python -m app.services.process_youtube
uv run python -m app.services.process_digest

# Test curation
uv run python -m app.services.process_curator

# Test email (be careful - will send real email!)
uv run python -m app.services.process_email
```

### 3. Test Full Pipeline

```bash
# Run full pipeline
uv run main.py
```

## Common Issues and Solutions

### Database Connection Failures

**Symptoms:**
- "Connection refused" errors
- Timeout errors
- SSL/TLS errors

**Solutions:**
- Verify database is running and accessible
- Check firewall/security group rules
- Verify connection string format
- Ensure database credentials are correct
- Check if SSL is required (add `?sslmode=require` to connection string)

### Container Startup Failures

**Symptoms:**
- Container exits immediately
- "Permission denied" errors
- Missing dependencies

**Solutions:**
- Check container logs
- Verify all environment variables are set
- Ensure Dockerfile includes all dependencies
- Check file permissions in container
- Verify entry point command is correct

### Scheduled Job Not Running

**Symptoms:**
- Job doesn't execute at scheduled time
- No logs appear
- Scheduler shows errors

**Solutions:**
- Verify scheduler configuration (cron syntax)
- Check timezone settings
- Verify permissions for scheduler service account
- Check scheduler logs
- Test manual trigger first

### Secrets Not Accessible

**Symptoms:**
- "Secret not found" errors
- Authentication failures
- Permission denied errors

**Solutions:**
- Verify secret exists in secrets management service
- Check IAM/service account permissions
- Verify secret name/key matches configuration
- Test secret access manually

## Cost Optimization Tips

1. **Use Serverless Containers**: Pay only when running (Cloud Run, Fargate)
2. **Right-Size Resources**: Start with minimum CPU/memory, scale up if needed
3. **Database Tier**: Use smallest instance that meets performance needs
4. **Scheduled Execution**: Run only when needed (daily), not continuously
5. **Image Optimization**: Use multi-stage builds, minimize image size
6. **Log Retention**: Set appropriate log retention periods
7. **Reserved Instances**: For predictable workloads, consider reserved capacity

## Security Best Practices

1. **Never Commit Secrets**: Use secrets management services
2. **Use Private Networks**: Connect containers to databases via private networks
3. **Enable SSL/TLS**: Use encrypted database connections
4. **Least Privilege**: Grant minimum required permissions
5. **Regular Updates**: Keep base images and dependencies updated
6. **Monitor Access**: Log and monitor all database access
7. **Rotate Secrets**: Regularly rotate API keys and passwords
8. **Network Isolation**: Use VPCs/VNets to isolate resources

## Monitoring Checklist

- [ ] Container execution logs are accessible
- [ ] Database connection monitoring is set up
- [ ] Job execution success/failure alerts configured
- [ ] Error tracking and notification system in place
- [ ] Resource usage monitoring (CPU, memory, storage)
- [ ] Cost monitoring and alerts configured
- [ ] Database performance metrics tracked

## Deployment Checklist

- [ ] Docker image builds successfully
- [ ] Database is created and accessible
- [ ] Secrets are stored securely
- [ ] Container registry is configured
- [ ] Container runtime is set up
- [ ] Scheduler is configured correctly
- [ ] Networking allows container-to-database communication
- [ ] Environment variables are set correctly
- [ ] Database tables are initialized
- [ ] Monitoring and logging are configured
- [ ] Test execution is successful
- [ ] Scheduled job runs successfully

## Next Steps

1. Choose your cloud provider
2. Follow provider-specific guide:
   - AWS: See `docs/AWS_DEPLOYMENT.md`
   - GCP: See `docs/GCP_DEPLOYMENT.md`
3. Or follow this general guide for other providers
4. Test thoroughly before production use
5. Set up monitoring and alerts
6. Document your specific deployment configuration

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Cron Expression Guide](https://crontab.guru/)
- [Container Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Database Security Best Practices](https://www.postgresql.org/docs/current/security.html)

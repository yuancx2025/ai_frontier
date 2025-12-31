# AWS Deployment Guide: ECS Fargate + EventBridge + RDS

This guide walks you through deploying the AI News Aggregator to AWS using:
- **ECS Fargate**: Serverless container execution
- **EventBridge**: Scheduled daily execution
- **RDS PostgreSQL**: Managed database service
- **ECR**: Docker image registry
- **Secrets Manager**: Secure credential storage

## Architecture Overview

```
EventBridge (Cron Schedule)
    ↓ triggers daily
ECS Fargate Task
    ↓ connects to
RDS PostgreSQL
    ↓ uses
ECR (Docker Images)
    ↓ stores secrets in
Secrets Manager
```

## Prerequisites

- AWS Account
- AWS CLI installed and configured (`aws configure`)
- Docker installed locally
- Basic knowledge of AWS services

## Step-by-Step Deployment

### Step 1: Set Up AWS CLI and Configure Region

```bash
# Install AWS CLI (if not installed)
# macOS: brew install awscli
# Linux: sudo apt-get install awscli

# Configure AWS credentials
aws configure

# Set your default region (e.g., us-east-1)
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### Step 2: Create RDS PostgreSQL Instance

```bash
# Create DB subnet group (if you don't have one)
aws rds create-db-subnet-group \
  --db-subnet-group-name ai-news-db-subnet-group \
  --db-subnet-group-description "Subnet group for AI News Aggregator" \
  --subnet-ids subnet-xxx subnet-yyy \
  --tags Key=Name,Value=ai-news-db-subnet-group

# Create security group for RDS
aws ec2 create-security-group \
  --group-name ai-news-db-sg \
  --description "Security group for AI News Aggregator RDS" \
  --vpc-id vpc-xxx

# Get security group ID
DB_SG_ID=$(aws ec2 describe-security-groups \
  --group-names ai-news-db-sg \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Create RDS PostgreSQL instance
aws rds create-db-instance \
  --db-instance-identifier ai-news-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password YourSecurePassword123! \
  --allocated-storage 20 \
  --storage-type gp3 \
  --vpc-security-group-ids $DB_SG_ID \
  --db-subnet-group-name ai-news-db-subnet-group \
  --backup-retention-period 7 \
  --storage-encrypted \
  --publicly-accessible \
  --tags Key=Name,Value=ai-news-db

# Wait for instance to be available (this takes 5-10 minutes)
aws rds wait db-instance-available --db-instance-identifier ai-news-db

# Get endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier ai-news-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "Database endpoint: $DB_ENDPOINT"
```

**Note**: For production, consider:
- Using private subnets
- Enabling Multi-AZ for high availability
- Using a larger instance type (db.t3.small or larger)

### Step 3: Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name ai-frontier \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# Get repository URI
ECR_REPO=$(aws ecr describe-repositories \
  --repository-names ai-frontier \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR Repository: $ECR_REPO"
```

### Step 4: Build and Push Docker Image

**Option A: Build Locally and Push (Recommended for first-time setup)**

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build Docker image
docker build -f deployment/Dockerfile -t ai-frontier .

# Tag image
docker tag ai-frontier:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:latest
```

**Option B: Use AWS CodeBuild (For CI/CD)**

If you want automated builds when you push to Git, you can use AWS CodeBuild with the `buildspec.yml` file at the project root:

1. Create a CodeBuild project in AWS Console
2. Point it to your Git repository
3. CodeBuild will automatically use `buildspec.yml` (at root) to build and push to ECR

The `buildspec.yml` file is optional - you can always build locally and push manually.

### Step 5: Store Secrets in Secrets Manager

```bash
# Store Gemini API key
aws secretsmanager create-secret \
  --name ai-news/gemini-api-key \
  --secret-string "your_gemini_api_key_here" \
  --description "Gemini API key for AI News Aggregator"

# Store email
aws secretsmanager create-secret \
  --name ai-news/my-email \
  --secret-string "your_email@gmail.com" \
  --description "Email address for sending digests"

# Store app password
aws secretsmanager create-secret \
  --name ai-news/app-password \
  --secret-string "your_gmail_app_password" \
  --description "Gmail app password for SMTP"

# Store database password
aws secretsmanager create-secret \
  --name ai-news/db-password \
  --secret-string "YourSecurePassword123!" \
  --description "RDS PostgreSQL password"
```

### Step 6: Create IAM Roles and Policies

```bash
# Create execution role for ECS tasks
aws iam create-role \
  --role-name ai-news-ecs-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach execution role policy
aws iam attach-role-policy \
  --role-name ai-news-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create policy for Secrets Manager access
aws iam create-policy \
  --policy-name ai-news-secrets-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:'$AWS_REGION':'$AWS_ACCOUNT_ID':secret:ai-news/*"
      ]
    }]
  }'

# Attach secrets policy to execution role
SECRETS_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-secrets-access`].Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ai-news-ecs-execution-role \
  --policy-arn $SECRETS_POLICY_ARN

# Create role for EventBridge to run ECS tasks
aws iam create-role \
  --role-name ai-news-eventbridge-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policy for EventBridge to run ECS tasks
aws iam attach-role-policy \
  --role-name ai-news-eventbridge-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess
```

### Step 7: Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name ai-frontier-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1 \
    capacityProvider=FARGATE_SPOT,weight=0

# Get VPC and subnet IDs (you'll need these for the task definition)
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].SubnetId' \
  --output text | tr '\t' ',')

echo "VPC ID: $VPC_ID"
echo "Subnet IDs: $SUBNET_IDS"
```

### Step 8: Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "ai-frontier",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ai-news-ecs-execution-role",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ai-news-ecs-execution-role",
  "containerDefinitions": [
    {
      "name": "ai-frontier",
      "image": "ECR_REPO_URI:latest",
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "PRODUCTION"
        }
      ],
      "secrets": [
        {
          "name": "GEMINI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/gemini-api-key"
        },
        {
          "name": "MY_EMAIL",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/my-email"
        },
        {
          "name": "APP_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/app-password"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-frontier",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**Before creating the task definition**, create the database URL secret:

```bash
# Construct database URL
DB_URL="postgresql://postgres:YourSecurePassword123!@$DB_ENDPOINT:5432/ai_news_aggregator"

# Store database URL
aws secretsmanager create-secret \
  --name ai-news/database-url \
  --secret-string "$DB_URL" \
  --description "RDS PostgreSQL connection string"
```

Now create the task definition:

```bash
# Replace placeholders in task definition
sed -i.bak "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" ecs-task-definition.json
sed -i.bak "s/REGION/$AWS_REGION/g" ecs-task-definition.json
sed -i.bak "s|ECR_REPO_URI|$ECR_REPO|g" ecs-task-definition.json

# Create CloudWatch log group
aws logs create-log-group --log-group-name /ecs/ai-frontier

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Get task definition ARN
TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition ai-frontier \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)
```

### Step 9: Create Security Group for ECS Tasks

```bash
# Create security group for ECS tasks
aws ec2 create-security-group \
  --group-name ai-news-ecs-sg \
  --description "Security group for ECS tasks" \
  --vpc-id $VPC_ID

ECS_SG_ID=$(aws ec2 describe-security-groups \
  --group-names ai-news-ecs-sg \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow ECS tasks to access RDS
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG_ID
```

### Step 10: Create EventBridge Rule

```bash
# Create EventBridge rule for daily execution (5 AM UTC)
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 5 * * ? *)" \
  --state ENABLED \
  --description "Daily AI News Aggregator execution"

# Get EventBridge role ARN
EVENTBRIDGE_ROLE_ARN=$(aws iam get-role \
  --role-name ai-news-eventbridge-role \
  --query 'Role.Arn' \
  --output text)

# Add ECS task as target
aws events put-targets \
  --rule daily-digest-schedule \
  --targets "[{
    \"Id\": \"1\",
    \"Arn\": \"arn:aws:ecs:$AWS_REGION:$AWS_ACCOUNT_ID:cluster/ai-frontier-cluster\",
    \"RoleArn\": \"$EVENTBRIDGE_ROLE_ARN\",
    \"EcsParameters\": {
      \"TaskDefinitionArn\": \"$TASK_DEF_ARN\",
      \"LaunchType\": \"FARGATE\",
      \"NetworkConfiguration\": {
        \"awsvpcConfiguration\": {
          \"Subnets\": [\"$(echo $SUBNET_IDS | cut -d',' -f1)\"],
          \"SecurityGroups\": [\"$ECS_SG_ID\"],
          \"AssignPublicIp\": \"ENABLED\"
        }
      }
    }
  }]"
```

### Step 11: Initialize Database Tables

Run the database initialization manually:

```bash
# Run a one-time ECS task to initialize database
aws ecs run-task \
  --cluster ai-frontier-cluster \
  --task-definition ai-frontier \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$(echo $SUBNET_IDS | cut -d',' -f1)],securityGroups=[$ECS_SG_ID],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "ai-frontier",
      "command": ["uv", "run", "python", "-m", "app.database.create_tables"]
    }]
  }'
```

## Monitoring and Logs

### View Logs

```bash
# View CloudWatch logs
aws logs tail /ecs/ai-frontier --follow

# Or view in AWS Console:
# CloudWatch → Log groups → /ecs/ai-frontier
```

### Check EventBridge Rule Status

```bash
# List rules
aws events list-rules --name-prefix daily-digest

# Check rule targets
aws events list-targets-by-rule --rule daily-digest-schedule
```

### Monitor ECS Tasks

```bash
# List recent tasks
aws ecs list-tasks --cluster ai-frontier-cluster

# Describe task
aws ecs describe-tasks \
  --cluster ai-frontier-cluster \
  --tasks TASK_ID
```

## Cost Estimation

**Monthly costs (approximate):**
- RDS PostgreSQL (db.t3.micro): ~$15/month
- ECS Fargate (512 CPU, 1GB RAM, ~30 min/day): ~$3-5/month
- ECR storage (5GB): ~$0.50/month
- Secrets Manager (4 secrets): Free (first 10,000 API calls/month)
- EventBridge: Free (first 1 million events/month)
- Data transfer: ~$1-2/month

**Total: ~$20-25/month**

## Troubleshooting

### Task Fails to Start

1. Check CloudWatch logs for errors
2. Verify secrets are accessible:
   ```bash
   aws secretsmanager get-secret-value --secret-id ai-news/gemini-api-key
   ```
3. Check IAM roles have correct permissions
4. Verify security groups allow traffic

### Database Connection Issues

1. Verify RDS security group allows traffic from ECS security group
2. Check database endpoint is correct
3. Verify database credentials in Secrets Manager
4. Test connection manually:
   ```bash
   psql -h $DB_ENDPOINT -U postgres -d ai_news_aggregator
   ```

### EventBridge Not Triggering

1. Check rule is enabled:
   ```bash
   aws events describe-rule --name daily-digest-schedule
   ```
2. Verify target configuration
3. Check CloudWatch Events logs for errors

## Updating the Deployment

### Update Docker Image

**Option A: Build Locally**

```bash
# Rebuild and push
docker build -f deployment/Dockerfile -t ai-frontier .
docker tag ai-frontier:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Update ECS service (if using service instead of scheduled tasks)
aws ecs update-service \
  --cluster ai-frontier-cluster \
  --service ai-frontier \
  --force-new-deployment
```

**Option B: Use CodeBuild**

If you've set up CodeBuild with `buildspec.yml` (at root), simply push to your Git repository and CodeBuild will automatically rebuild and push the new image.

### Update Environment Variables

Update secrets in Secrets Manager, then restart tasks:

```bash
aws secretsmanager update-secret \
  --secret-id ai-news/gemini-api-key \
  --secret-string "new_api_key"
```

## Cleanup

To remove all resources:

```bash
# Delete EventBridge rule
aws events remove-targets --rule daily-digest-schedule --ids 1
aws events delete-rule --name daily-digest-schedule

# Delete ECS task definition
aws ecs deregister-task-definition --task-definition ai-frontier

# Delete ECS cluster
aws ecs delete-cluster --cluster ai-frontier-cluster

# Delete RDS instance
aws rds delete-db-instance \
  --db-instance-identifier ai-news-db \
  --skip-final-snapshot

# Delete secrets
aws secretsmanager delete-secret --secret-id ai-news/gemini-api-key --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id ai-news/my-email --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id ai-news/app-password --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id ai-news/database-url --force-delete-without-recovery

# Delete ECR repository
aws ecr delete-repository \
  --repository-name ai-frontier \
  --force

# Delete IAM roles
aws iam detach-role-policy --role-name ai-news-ecs-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam delete-role --role-name ai-news-ecs-execution-role
aws iam delete-role --role-name ai-news-eventbridge-role
```

## Additional Resources

- [ECS Fargate Documentation](https://docs.aws.amazon.com/ecs/latest/developerguide/AWS_Fargate.html)
- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)

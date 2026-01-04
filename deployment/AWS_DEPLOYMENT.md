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
    ↓ triggers daily/weekly
ECS Fargate Task
    ↓ runs main.py → daily_runner.py
    ├─ Scrapes articles (shared across all users)
    ├─ Generates personalized digests (per user)
    └─ Sends personalized emails (per user)
    ↓ connects to
RDS PostgreSQL (stores users, articles, digests)
    ↓ uses
ECR (Docker Images)
    ↓ stores secrets in
Secrets Manager
```

### Multi-User Support

The system supports multiple users, each with personalized preferences:
- **User Profiles**: Stored in RDS PostgreSQL `users` table
- **Personalized Digests**: Each user gets digests scored based on their profile
- **Personalized Emails**: Each active user receives their own email digest
- **User Management**: Use the Gradio UI (`python main.py --ui`) or the predefined user script (`python scripts/create_predefined_users.py`) to create/update users locally, or manage via database directly

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

# Store SES from email (for email sending via AWS SES)
aws secretsmanager create-secret \
  --name ai-news/ses-from-email \
  --secret-string "your_verified_ses_email@example.com" \
  --description "Verified SES email address for sending digests"

# Optional: Store Gmail credentials (if using Gmail SMTP instead of SES)
# aws secretsmanager create-secret \
#   --name ai-news/my-email \
#   --secret-string "your_email@gmail.com" \
#   --description "Email address for sending digests"
# 
# aws secretsmanager create-secret \
#   --name ai-news/app-password \
#   --secret-string "your_gmail_app_password" \
#   --description "Gmail app password for SMTP"

# Store database password
aws secretsmanager create-secret \
  --name ai-news/db-password \
  --secret-string "YourSecurePassword123!" \
  --description "RDS PostgreSQL password"
```

### Step 6: Create IAM Roles and Policies

**Important**: We create separate roles for execution (ECS pulling images/secrets) and task (application accessing AWS services).

```bash
# 1. Execution Role (for ECS to pull images and secrets)
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

# Create policy for Secrets Manager access (for execution role)
# Note: Using proper variable expansion with double quotes
cat > /tmp/secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ],
    "Resource": [
      "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ai-news/*"
    ]
  }]
}
EOF

aws iam create-policy \
  --policy-name ai-news-secrets-access \
  --policy-document file:///tmp/secrets-policy.json

# Attach secrets policy to execution role
SECRETS_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-secrets-access`].Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ai-news-ecs-execution-role \
  --policy-arn $SECRETS_POLICY_ARN

# 2. Task Role (for tasks to access AWS services like SES, Secrets Manager)
aws iam create-role \
  --role-name ai-news-ecs-task-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Create policy for task role (SES, Secrets Manager, etc.)
cat > /tmp/task-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ai-news/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ai-news-task-policy \
  --policy-document file:///tmp/task-policy.json

# Attach task policy
TASK_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-task-policy`].Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ai-news-ecs-task-role \
  --policy-arn $TASK_POLICY_ARN

# 3. EventBridge role (for triggering tasks)
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

# Get execution and task role ARNs for the policy
EXECUTION_ROLE_ARN=$(aws iam get-role \
  --role-name ai-news-ecs-execution-role \
  --query 'Role.Arn' \
  --output text)

TASK_ROLE_ARN=$(aws iam get-role \
  --role-name ai-news-ecs-task-role \
  --query 'Role.Arn' \
  --output text)

# Create minimal custom policy for EventBridge (instead of FullAccess)
cat > /tmp/eventbridge-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask"
      ],
      "Resource": "arn:aws:ecs:${AWS_REGION}:${AWS_ACCOUNT_ID}:task-definition/ai-frontier:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "${EXECUTION_ROLE_ARN}",
        "${TASK_ROLE_ARN}"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name ai-news-eventbridge-policy \
  --policy-document file:///tmp/eventbridge-policy.json

EVENTBRIDGE_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-eventbridge-policy`].Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name ai-news-eventbridge-role \
  --policy-arn $EVENTBRIDGE_POLICY_ARN
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

# Get VPC ID
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

# Get public subnets (for cost savings - no NAT Gateway needed)
PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" \
  --query 'Subnets[*].SubnetId' \
  --output text | tr '\t' ',')

# Fallback to all subnets if no public subnets found
if [ -z "$PUBLIC_SUBNETS" ]; then
  PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text | tr '\t' ',')
fi

echo "VPC ID: $VPC_ID"
echo "Public Subnet IDs: $PUBLIC_SUBNETS"
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
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ai-news-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "ai-frontier",
      "image": "ECR_REPO_URI:latest",
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "PRODUCTION"
        },
        {
          "name": "MODE",
          "value": "pipeline"
        },
        {
          "name": "HOURS",
          "value": "24"
        },
        {
          "name": "TOP_N",
          "value": "10"
        }
      ],
      "secrets": [
      {
        "name": "GEMINI_API_KEY",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/gemini-api-key"
      },
      {
        "name": "YOUTUBE_API_KEY",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/youtube-api-key"
      },
      {
        "name": "DATABASE_URL",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/database-url"
      },
      {
        "name": "SES_FROM_EMAIL",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:ai-news/ses-from-email"
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

### Step 9: Initialize Database Tables

Run the database initialization manually before creating the EventBridge schedule:

```bash
# Get pipeline security group ID (we'll create it in the next step, but we need it here)
# For now, we'll create the security group first, then run the init task
# Create security group for pipeline tasks (NO inbound rules - outbound only)
aws ec2 create-security-group \
  --group-name ai-frontier-pipeline-sg \
  --description "Security group for pipeline tasks - outbound only" \
  --vpc-id $VPC_ID

PIPELINE_SG_ID=$(aws ec2 describe-security-groups \
  --group-names ai-frontier-pipeline-sg \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow RDS access from pipeline tasks
aws ec2 authorize-security-group-ingress \
  --group-id $DB_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $PIPELINE_SG_ID

# Get public subnets (needed for task execution)
PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" \
  --query 'Subnets[*].SubnetId' \
  --output text | tr '\t' ',')

# Fallback to all subnets if no public subnets found
if [ -z "$PUBLIC_SUBNETS" ]; then
  PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[*].SubnetId' \
    --output text | tr '\t' ',')
fi

# Run a one-time ECS task to initialize database
# Use pipeline security group and multiple subnets
SUBNET_ARRAY=$(echo $PUBLIC_SUBNETS | tr ',' ' ' | awk '{print "[\""$1"\",\""$2"\"]"}')
if [ $(echo $PUBLIC_SUBNETS | tr ',' '\n' | wc -l) -lt 2 ]; then
  SUBNET_ARRAY="[\"$(echo $PUBLIC_SUBNETS | cut -d',' -f1)\"]"
fi

aws ecs run-task \
  --cluster ai-frontier-cluster \
  --task-definition ai-frontier \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=$SUBNET_ARRAY,securityGroups=[$PIPELINE_SG_ID],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "ai-frontier",
      "command": ["uv", "run", "python", "-c", "from app.database.connection import create_all_tables; create_all_tables()"]
    }]
  }'

# Note: uv is installed in the Docker image (see Dockerfile), so this command works

# Wait for task to complete
aws ecs wait tasks-stopped --cluster ai-frontier-cluster

echo "Pipeline Security Group: $PIPELINE_SG_ID"
```

**Note**: The pipeline will automatically create tables if they don't exist, but it's good practice to initialize them first.

### Step 10: Create Security Groups

**Important**: We only need the pipeline security group (already created in Step 9, but listed here for completeness):

```bash
# Create security group for pipeline tasks (if not already created in Step 9)
if [ -z "$PIPELINE_SG_ID" ]; then
  aws ec2 create-security-group \
    --group-name ai-frontier-pipeline-sg \
    --description "Security group for pipeline tasks - outbound only" \
    --vpc-id $VPC_ID

  PIPELINE_SG_ID=$(aws ec2 describe-security-groups \
    --group-names ai-frontier-pipeline-sg \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

  # Allow RDS access from pipeline tasks
  aws ec2 authorize-security-group-ingress \
    --group-id $DB_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $PIPELINE_SG_ID
fi

echo "Pipeline Security Group: $PIPELINE_SG_ID"
```

### Step 11: Create EventBridge Rule

```bash
# Create EventBridge rule for daily execution
# Note: Cron expressions are in UTC timezone
# "cron(0 5 * * ? *)" = 5:00 AM UTC daily
# To convert to your timezone:
#   - EST (UTC-5): 5 AM UTC = 12:00 AM EST
#   - PST (UTC-8): 5 AM UTC = 9:00 PM PST (previous day)
#   - Use EventBridge Scheduler for timezone-aware scheduling if needed
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 5 * * ? *)" \
  --state ENABLED \
  --description "Daily AI News Aggregator execution (5 AM UTC)"

# Get EventBridge role ARN
EVENTBRIDGE_ROLE_ARN=$(aws iam get-role \
  --role-name ai-news-eventbridge-role \
  --query 'Role.Arn' \
  --output text)

# Add ECS task as target (in public subnets, using pipeline security group)
# Use at least 2 subnets for better availability
SUBNET_ARRAY=$(echo $PUBLIC_SUBNETS | tr ',' ' ' | awk '{print "[\""$1"\",\""$2"\"]"}')
# Fallback to single subnet if only one available
if [ $(echo $PUBLIC_SUBNETS | tr ',' '\n' | wc -l) -lt 2 ]; then
  SUBNET_ARRAY="[\"$(echo $PUBLIC_SUBNETS | cut -d',' -f1)\"]"
fi

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
          \"Subnets\": $SUBNET_ARRAY,
          \"SecurityGroups\": [\"$PIPELINE_SG_ID\"],
          \"AssignPublicIp\": \"ENABLED\"
        }
      }
    }
  }]"
```

### Step 12: Create Initial User Profile (Optional)

The system requires at least one active user to send emails. You can create users in three ways:

**Option A: Using the Predefined User Script (Recommended)**

```bash
# Edit scripts/create_predefined_users.py to add your user(s)
# Then run the script locally (requires database connection)
python scripts/create_predefined_users.py
```

**Option B: Using the Gradio UI (Local Development)**

```bash
# Run locally with UI mode
python main.py --ui

# Then access http://127.0.0.1:7860 in your browser
# Create a user profile with your preferences
```

**Option C: Direct Database Insert**

```bash
# Connect to your RDS instance
psql -h $DB_ENDPOINT -U postgres -d ai_news_aggregator

# Insert a user directly
INSERT INTO users (id, email, name, title, background, content_preferences, preferences, expertise_level, is_active, created_at, updated_at)
VALUES (
  gen_random_uuid()::text,
  'your_email@example.com',
  'Your Name',
  'Your Title',
  'Your background description',
  '["research", "technique", "education"]'::json,
  '{"prefer_practical": true, "prefer_technical_depth": true}'::json,
  'Medium',
  true,
  NOW(),
  NOW()
);
```

**Important**: Make sure the email address matches a verified SES email address if using AWS SES for email delivery.

## How the Daily Pipeline Works

When EventBridge triggers the Fargate task, it runs `main.py`, which executes the following pipeline:

1. **Scraping Phase**: Scrapes articles from all configured sources (YouTube, OpenAI, Anthropic, etc.)
   - Results are stored in the database (shared across all users)

2. **Digest Generation Phase**: For each active user:
   - Retrieves articles from the scraping phase
   - Generates personalized digests with relevance scores based on user profile
   - Stores digests in the database

3. **Email Delivery Phase**: For each active user:
   - Generates a personalized email digest with top N articles
   - Sends email to the user's email address
   - Marks digests as sent

**Multi-User Behavior**:
- If you have 3 active users, the system will:
  - Generate 3 sets of personalized digests (one per user)
  - Send 3 personalized emails (one per user)
- Each user receives content tailored to their preferences and interests

## Monitoring and Logs

### View Logs

```bash
# View CloudWatch logs (real-time)
aws logs tail /ecs/ai-frontier --follow

# View recent logs
aws logs tail /ecs/ai-frontier --since 1h

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

1. Verify RDS security group allows traffic from pipeline security group:
   ```bash
   # Check RDS security group rules
   aws ec2 describe-security-groups --group-ids $DB_SG_ID
   ```
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
4. Verify the cron expression matches your timezone (default is 5 AM UTC)

### No Users Receiving Emails

1. Check if users exist and are active:
   ```bash
   # Connect to database
   psql -h $DB_ENDPOINT -U postgres -d ai_news_aggregator
   
   # Check users
   SELECT email, name, is_active FROM users;
   ```
2. Verify SES email addresses are verified (if using SES)
3. Check CloudWatch logs for email sending errors
4. Ensure user email addresses match verified SES addresses

## Updating the Deployment

### Update Docker Image

**Option A: Build Locally**

```bash
# Rebuild and push
docker build -f deployment/Dockerfile -t ai-frontier .
docker tag ai-frontier:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Note: For scheduled tasks (EventBridge), new task definitions will be used automatically
# on the next scheduled run. To test immediately, manually trigger a task run.
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

# Delete security groups
# Get security group IDs first
PIPELINE_SG_ID=$(aws ec2 describe-security-groups \
  --group-names ai-frontier-pipeline-sg \
  --query 'SecurityGroups[0].GroupId' \
  --output text)
DB_SG_ID=$(aws ec2 describe-security-groups \
  --group-names ai-news-db-sg \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

aws ec2 delete-security-group --group-id $PIPELINE_SG_ID
aws ec2 delete-security-group --group-id $DB_SG_ID

# Delete secrets
aws secretsmanager delete-secret --secret-id ai-news/gemini-api-key --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id ai-news/ses-from-email --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id ai-news/database-url --force-delete-without-recovery
# Optional: Delete Gmail secrets if you created them
# aws secretsmanager delete-secret --secret-id ai-news/my-email --force-delete-without-recovery
# aws secretsmanager delete-secret --secret-id ai-news/app-password --force-delete-without-recovery

# Delete ECR repository
aws ecr delete-repository \
  --repository-name ai-frontier \
  --force

# Delete IAM policies and roles
# Get policy ARNs
SECRETS_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-secrets-access`].Arn' \
  --output text)
TASK_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-task-policy`].Arn' \
  --output text)
EVENTBRIDGE_POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`ai-news-eventbridge-policy`].Arn' \
  --output text)

# Detach and delete policies
aws iam detach-role-policy --role-name ai-news-ecs-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam detach-role-policy --role-name ai-news-ecs-execution-role --policy-arn $SECRETS_POLICY_ARN
aws iam detach-role-policy --role-name ai-news-ecs-task-role --policy-arn $TASK_POLICY_ARN
aws iam detach-role-policy --role-name ai-news-eventbridge-role --policy-arn $EVENTBRIDGE_POLICY_ARN

# Delete policies
aws iam delete-policy --policy-arn $SECRETS_POLICY_ARN
aws iam delete-policy --policy-arn $TASK_POLICY_ARN
aws iam delete-policy --policy-arn $EVENTBRIDGE_POLICY_ARN

# Delete roles
aws iam delete-role --role-name ai-news-ecs-execution-role
aws iam delete-role --role-name ai-news-ecs-task-role
aws iam delete-role --role-name ai-news-eventbridge-role

# Delete CloudWatch log group
aws logs delete-log-group --log-group-name /ecs/ai-frontier
```

## Customizing the Schedule

**Important**: EventBridge cron expressions use UTC timezone. To convert to your local timezone:
- EST (UTC-5): Subtract 5 hours (e.g., 5 AM UTC = 12:00 AM EST)
- PST (UTC-8): Subtract 8 hours (e.g., 5 AM UTC = 9:00 PM PST previous day)
- For timezone-aware scheduling, consider using EventBridge Scheduler instead of cron rules

To change when the pipeline runs, update the EventBridge rule:

```bash
# Update to run weekly (every Monday at 5 AM UTC)
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 5 ? * MON *)" \
  --state ENABLED

# Update to run twice daily (5 AM and 5 PM UTC)
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 5,17 * * ? *)" \
  --state ENABLED

# Update to run every 6 hours (UTC)
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 */6 * * ? *)" \
  --state ENABLED

# Example: Run at 5 AM EST (10 AM UTC during standard time)
# Note: Adjust for daylight saving time if needed
aws events put-rule \
  --name daily-digest-schedule \
  --schedule-expression "cron(0 10 * * ? *)" \
  --state ENABLED
```

## Adjusting Pipeline Parameters

You can adjust `HOURS` and `TOP_N` parameters in the ECS task definition:

- **HOURS**: How many hours back to look for articles (default: 24)
- **TOP_N**: How many top articles to include in email (default: 10)

Update the task definition and create a new revision:

```bash
# Edit ecs-task-definition.json to change HOURS or TOP_N values
# Then register a new revision
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Update EventBridge target to use new task definition
TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition ai-frontier \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

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

## Additional Resources

- [ECS Fargate Documentation](https://docs.aws.amazon.com/ecs/latest/developerguide/AWS_Fargate.html)
- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)

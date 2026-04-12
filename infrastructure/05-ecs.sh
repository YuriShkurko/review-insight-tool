#!/usr/bin/env bash
# Step 5 — ECS Cluster + task definitions + services.
# Registers task definitions and creates Fargate services pointing at the ALB.
# Requires: ECR images already pushed (run `make deploy-push` or let CD do it first).
# Safe to re-run.
set -euo pipefail
source "$(dirname "$0")/config.sh"

# Fetch values from SSM
TG_BACKEND_ARN=$(aws ssm get-parameter --name "/review-insight/TG_BACKEND_ARN" \
  --query Parameter.Value --output text --region "$AWS_REGION")
TG_FRONTEND_ARN=$(aws ssm get-parameter --name "/review-insight/TG_FRONTEND_ARN" \
  --query Parameter.Value --output text --region "$AWS_REGION")
SG_ECS_ID=$(aws ssm get-parameter --name "/review-insight/SG_ECS_ID" \
  --query Parameter.Value --output text --region "$AWS_REGION")
SUBNET_IDS=$(aws ssm get-parameter --name "/review-insight/SUBNET_IDS" \
  --query Parameter.Value --output text --region "$AWS_REGION")

EXECUTION_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole"
SUBNET_JSON=$(echo "$SUBNET_IDS" | tr ',' '\n' | jq -R . | jq -sc .)

# ── ECS Cluster ───────────────────────────────────────────────────────────────
if aws ecs describe-clusters --clusters "$ECS_CLUSTER" \
     --region "$AWS_REGION" \
     --query "clusters[?status=='ACTIVE'].clusterName" \
     --output text | grep -q "$ECS_CLUSTER"; then
  echo "✓ ECS cluster already exists: $ECS_CLUSTER"
else
  aws ecs create-cluster \
    --cluster-name "$ECS_CLUSTER" \
    --capacity-providers FARGATE FARGATE_SPOT \
    --region "$AWS_REGION" --output table
  echo "✓ Created ECS cluster: $ECS_CLUSTER"
fi

# ── Backend task definition ───────────────────────────────────────────────────
echo "Registering backend task definition..."
aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --family "${APP}-backend" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "512" \
  --memory "1024" \
  --execution-role-arn "$EXECUTION_ROLE_ARN" \
  --container-definitions "[
    {
      \"name\": \"backend\",
      \"image\": \"${ECR_BACKEND}:latest\",
      \"portMappings\": [{\"containerPort\": 8000, \"protocol\": \"tcp\"}],
      \"essential\": true,
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/${APP}-backend\",
          \"awslogs-region\": \"${AWS_REGION}\",
          \"awslogs-stream-prefix\": \"ecs\",
          \"awslogs-create-group\": \"true\"
        }
      },
      \"secrets\": [
        {\"name\": \"DATABASE_URL\",      \"valueFrom\": \"${SSM_DATABASE_URL}\"},
        {\"name\": \"OPENAI_API_KEY\",    \"valueFrom\": \"${SSM_OPENAI_KEY}\"},
        {\"name\": \"OUTSCRAPER_API_KEY\",\"valueFrom\": \"${SSM_OUTSCRAPER_KEY}\"},
        {\"name\": \"JWT_SECRET_KEY\",    \"valueFrom\": \"${SSM_JWT_SECRET}\"},
        {\"name\": \"MONGO_URI\",        \"valueFrom\": \"${SSM_MONGO_URI}\"}
      ],
      \"environment\": [
        {\"name\": \"REVIEW_PROVIDER\", \"value\": \"offline\"},
        {\"name\": \"CORS_ORIGINS\",    \"value\": \"*\"}
      ],
      \"healthCheck\": {
        \"command\": [\"CMD-SHELL\", \"curl -f http://localhost:8000/api/health || exit 1\"],
        \"interval\": 30,
        \"timeout\": 5,
        \"retries\": 3,
        \"startPeriod\": 60
      }
    }
  ]" --output table
echo "✓ Backend task definition registered"

# ── Frontend task definition ──────────────────────────────────────────────────
ALB_DNS=$(aws ssm get-parameter --name "/review-insight/ALB_DNS" \
  --query Parameter.Value --output text --region "$AWS_REGION")

echo "Registering frontend task definition..."
aws ecs register-task-definition \
  --region "$AWS_REGION" \
  --family "${APP}-frontend" \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu "256" \
  --memory "512" \
  --execution-role-arn "$EXECUTION_ROLE_ARN" \
  --container-definitions "[
    {
      \"name\": \"frontend\",
      \"image\": \"${ECR_FRONTEND}:latest\",
      \"portMappings\": [{\"containerPort\": 3000, \"protocol\": \"tcp\"}],
      \"essential\": true,
      \"logConfiguration\": {
        \"logDriver\": \"awslogs\",
        \"options\": {
          \"awslogs-group\": \"/ecs/${APP}-frontend\",
          \"awslogs-region\": \"${AWS_REGION}\",
          \"awslogs-stream-prefix\": \"ecs\",
          \"awslogs-create-group\": \"true\"
        }
      },
      \"environment\": [
        {\"name\": \"NODE_ENV\",            \"value\": \"production\"},
        {\"name\": \"NEXT_PUBLIC_API_URL\", \"value\": \"http://${ALB_DNS}\"}
      ]
    }
  ]" --output table
echo "✓ Frontend task definition registered"

# ── ECS Services ──────────────────────────────────────────────────────────────
create_or_update_service() {
  local name=$1 family=$2 port=$3 tg_arn=$4

  if aws ecs describe-services \
       --cluster "$ECS_CLUSTER" \
       --services "$name" \
       --region "$AWS_REGION" \
       --query "services[?status=='ACTIVE'].serviceName" \
       --output text | grep -q "$name"; then
    echo "✓ Service already exists: $name — forcing new deployment..."
    aws ecs update-service \
      --cluster "$ECS_CLUSTER" \
      --service "$name" \
      --force-new-deployment \
      --region "$AWS_REGION" --output table
  else
    TASK_DEF_ARN=$(aws ecs describe-task-definition \
      --task-definition "$family" \
      --query "taskDefinition.taskDefinitionArn" \
      --output text --region "$AWS_REGION")

    aws ecs create-service \
      --cluster "$ECS_CLUSTER" \
      --service-name "$name" \
      --task-definition "$TASK_DEF_ARN" \
      --desired-count 1 \
      --launch-type FARGATE \
      --network-configuration "awsvpcConfiguration={subnets=${SUBNET_JSON},securityGroups=[\"${SG_ECS_ID}\"],assignPublicIp=ENABLED}" \
      --load-balancers "targetGroupArn=${tg_arn},containerName=${family##*-},containerPort=${port}" \
      --health-check-grace-period-seconds 120 \
      --region "$AWS_REGION" --output table
    echo "✓ Created ECS service: $name"
  fi
}

create_or_update_service "${APP}-backend"  "${APP}-backend"  8000 "$TG_BACKEND_ARN"
create_or_update_service "${APP}-frontend" "${APP}-frontend" 3000 "$TG_FRONTEND_ARN"

echo ""
echo "✓ ECS setup complete."
echo "  Services are deploying — wait ~3 min then check:"
echo "  aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${APP}-backend ${APP}-frontend --region ${AWS_REGION} --query 'services[*].{name:serviceName,running:runningCount,desired:desiredCount,status:status}'"
echo ""
echo "  App will be available at: http://$(aws ssm get-parameter --name /review-insight/ALB_DNS --query Parameter.Value --output text --region $AWS_REGION)"

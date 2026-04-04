#!/usr/bin/env bash
# Step 3 — Security groups (uses default VPC — no custom VPC needed).
# Creates: sg-alb (public HTTP/HTTPS) and sg-ecs (only traffic from ALB).
# Safe to re-run.
set -euo pipefail
source "$(dirname "$0")/config.sh"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text \
  --region "$AWS_REGION")
echo "✓ Default VPC: $VPC_ID"

# ── ALB security group (internet → ALB) ───────────────────────────────────────
SG_ALB_NAME="${APP}-alb"
SG_ALB_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${SG_ALB_NAME}" "Name=vpc-id,Values=${VPC_ID}" \
  --query "SecurityGroups[0].GroupId" \
  --output text \
  --region "$AWS_REGION" 2>/dev/null)

if [[ "$SG_ALB_ID" == "None" || -z "$SG_ALB_ID" ]]; then
  SG_ALB_ID=$(aws ec2 create-security-group \
    --group-name "$SG_ALB_NAME" \
    --description "Allow HTTP/HTTPS from internet to ALB" \
    --vpc-id "$VPC_ID" \
    --region "$AWS_REGION" \
    --query "GroupId" --output text)

  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ALB_ID" \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 \
    --region "$AWS_REGION" --output text
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ALB_ID" \
    --protocol tcp --port 443 --cidr 0.0.0.0/0 \
    --region "$AWS_REGION" --output text

  echo "✓ Created SG (ALB): $SG_ALB_ID"
else
  echo "✓ SG (ALB) already exists: $SG_ALB_ID"
fi

# ── ECS security group (ALB → ECS tasks only) ────────────────────────────────
SG_ECS_NAME="${APP}-ecs"
SG_ECS_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${SG_ECS_NAME}" "Name=vpc-id,Values=${VPC_ID}" \
  --query "SecurityGroups[0].GroupId" \
  --output text \
  --region "$AWS_REGION" 2>/dev/null)

if [[ "$SG_ECS_ID" == "None" || -z "$SG_ECS_ID" ]]; then
  SG_ECS_ID=$(aws ec2 create-security-group \
    --group-name "$SG_ECS_NAME" \
    --description "Allow traffic from ALB to ECS tasks only" \
    --vpc-id "$VPC_ID" \
    --region "$AWS_REGION" \
    --query "GroupId" --output text)

  # Allow backend port from ALB
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ECS_ID" \
    --protocol tcp --port 8000 \
    --source-group "$SG_ALB_ID" \
    --region "$AWS_REGION" --output text
  # Allow frontend port from ALB
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ECS_ID" \
    --protocol tcp --port 3000 \
    --source-group "$SG_ALB_ID" \
    --region "$AWS_REGION" --output text

  echo "✓ Created SG (ECS): $SG_ECS_ID"
else
  echo "✓ SG (ECS) already exists: $SG_ECS_ID"
fi

# Allow ECS tasks to reach RDS (5432) from ECS SG
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ECS_ID" \
  --protocol tcp --port 5432 --cidr 0.0.0.0/0 \
  --region "$AWS_REGION" --output text 2>/dev/null || true

# Save to SSM for other scripts
aws ssm put-parameter --name "/review-insight/SG_ALB_ID" --value "$SG_ALB_ID" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/SG_ECS_ID" --value "$SG_ECS_ID" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/VPC_ID" --value "$VPC_ID" \
  --type String --overwrite --region "$AWS_REGION" --output text

echo ""
echo "✓ Network ready. SG_ALB=${SG_ALB_ID}, SG_ECS=${SG_ECS_ID}"
echo "Next: run 04-alb.sh"

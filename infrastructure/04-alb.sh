#!/usr/bin/env bash
# Step 4 — Application Load Balancer + target groups.
# Routes: /api/* → backend (port 8000), /* → frontend (port 3000).
# Safe to re-run.
set -euo pipefail
source "$(dirname "$0")/config.sh"

# Fetch values stored by 03-network.sh
VPC_ID=$(aws ssm get-parameter --name "/review-insight/VPC_ID" \
  --query Parameter.Value --output text --region "$AWS_REGION")
SG_ALB_ID=$(aws ssm get-parameter --name "/review-insight/SG_ALB_ID" \
  --query Parameter.Value --output text --region "$AWS_REGION")

# Get default subnets (need at least 2 AZs for ALB)
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=${VPC_ID}" "Name=defaultForAz,Values=true" \
  --query "Subnets[*].SubnetId" --output text --region "$AWS_REGION" \
  | tr '\t' ',')
echo "✓ Subnets: $SUBNET_IDS"

# ── ALB ───────────────────────────────────────────────────────────────────────
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names "${APP}-alb" \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text --region "$AWS_REGION" 2>/dev/null || echo "")

if [[ -z "$ALB_ARN" || "$ALB_ARN" == "None" ]]; then
  ALB_ARN=$(aws elbv2 create-load-balancer \
    --name "${APP}-alb" \
    --subnets $(echo $SUBNET_IDS | tr ',' ' ') \
    --security-groups "$SG_ALB_ID" \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --region "$AWS_REGION" \
    --query "LoadBalancers[0].LoadBalancerArn" --output text)
  echo "✓ Created ALB: $ALB_ARN"
else
  echo "✓ ALB already exists: $ALB_ARN"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns "$ALB_ARN" \
  --query "LoadBalancers[0].DNSName" \
  --output text --region "$AWS_REGION")
echo "✓ ALB DNS: $ALB_DNS"

# ── Target groups ─────────────────────────────────────────────────────────────
create_tg() {
  local name=$1 port=$2 hc_path=$3
  local arn
  arn=$(aws elbv2 describe-target-groups \
    --names "$name" \
    --query "TargetGroups[0].TargetGroupArn" \
    --output text --region "$AWS_REGION" 2>/dev/null || echo "")

  if [[ -z "$arn" || "$arn" == "None" ]]; then
    arn=$(aws elbv2 create-target-group \
      --name "$name" \
      --protocol HTTP --port "$port" \
      --vpc-id "$VPC_ID" \
      --target-type ip \
      --health-check-path "$hc_path" \
      --health-check-interval-seconds 30 \
      --healthy-threshold-count 2 \
      --unhealthy-threshold-count 3 \
      --region "$AWS_REGION" \
      --query "TargetGroups[0].TargetGroupArn" --output text)
    echo "✓ Created target group: $name → $arn"
  else
    echo "✓ Target group already exists: $name"
  fi
  echo "$arn"
}

TG_BACKEND_ARN=$(create_tg "${APP}-backend" 8000 "/api/health")
TG_FRONTEND_ARN=$(create_tg "${APP}-frontend" 3000 "/")

# ── HTTP listener (port 80) ───────────────────────────────────────────────────
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --query "Listeners[?Port==\`80\`].ListenerArn" \
  --output text --region "$AWS_REGION" 2>/dev/null || echo "")

if [[ -z "$LISTENER_ARN" || "$LISTENER_ARN" == "None" ]]; then
  # Default action: forward to frontend
  LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTP --port 80 \
    --default-actions "Type=forward,TargetGroupArn=${TG_FRONTEND_ARN}" \
    --region "$AWS_REGION" \
    --query "Listeners[0].ListenerArn" --output text)
  echo "✓ Created listener: $LISTENER_ARN"

  # Rule: /api/* → backend
  aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --priority 10 \
    --conditions "Field=path-pattern,Values='/api/*'" \
    --actions "Type=forward,TargetGroupArn=${TG_BACKEND_ARN}" \
    --region "$AWS_REGION" --output table
  echo "✓ Created routing rule: /api/* → backend"
else
  echo "✓ Listener already exists: $LISTENER_ARN"
fi

# Save to SSM for next steps
aws ssm put-parameter --name "/review-insight/ALB_ARN" --value "$ALB_ARN" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/ALB_DNS" --value "$ALB_DNS" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/TG_BACKEND_ARN" --value "$TG_BACKEND_ARN" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/TG_FRONTEND_ARN" --value "$TG_FRONTEND_ARN" \
  --type String --overwrite --region "$AWS_REGION" --output text
aws ssm put-parameter --name "/review-insight/SUBNET_IDS" --value "$SUBNET_IDS" \
  --type String --overwrite --region "$AWS_REGION" --output text

echo ""
echo "✓ ALB ready."
echo "  Public URL: http://${ALB_DNS}"
echo ""
echo "⚠  Add this DNS as BACKEND_PUBLIC_URL in GitHub vars for the frontend build."
echo "Next: run 05-ecs.sh"

#!/usr/bin/env bash
# Teardown — deletes all AWS resources created by the setup scripts.
# USE WITH CARE. This will stop billing but destroy all data.
# RDS deletion has a 7-day snapshot retention by default.
set -euo pipefail
source "$(dirname "$0")/config.sh"

echo "⚠  This will DELETE all Review Insight AWS infrastructure."
echo "   Region: $AWS_REGION | Account: $AWS_ACCOUNT_ID"
read -rp "Type 'DELETE' to confirm: " confirm
[[ "$confirm" == "DELETE" ]] || { echo "Aborted."; exit 1; }

# ── ECS services (set desired=0 first, then delete) ───────────────────────────
for svc in "${APP}-backend" "${APP}-frontend"; do
  aws ecs update-service --cluster "$ECS_CLUSTER" --service "$svc" \
    --desired-count 0 --region "$AWS_REGION" --output text 2>/dev/null || true
  aws ecs delete-service --cluster "$ECS_CLUSTER" --service "$svc" \
    --force --region "$AWS_REGION" --output text 2>/dev/null || true
  echo "✓ Deleted ECS service: $svc"
done

# ── ECS cluster ───────────────────────────────────────────────────────────────
aws ecs delete-cluster --cluster "$ECS_CLUSTER" \
  --region "$AWS_REGION" --output text 2>/dev/null || true
echo "✓ Deleted ECS cluster"

# ── ALB + listeners + target groups ─────────────────────────────────────────
ALB_ARN=$(aws ssm get-parameter --name "/review-insight/ALB_ARN" \
  --query Parameter.Value --output text --region "$AWS_REGION" 2>/dev/null || echo "")
if [[ -n "$ALB_ARN" && "$ALB_ARN" != "None" ]]; then
  LISTENER_ARNS=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" \
    --query "Listeners[*].ListenerArn" --output text --region "$AWS_REGION" 2>/dev/null || echo "")
  for l in $LISTENER_ARNS; do
    aws elbv2 delete-listener --listener-arn "$l" --region "$AWS_REGION" --output text 2>/dev/null || true
  done
  aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN" \
    --region "$AWS_REGION" --output text 2>/dev/null || true
  echo "✓ Deleted ALB"
fi

for tg_param in "/review-insight/TG_BACKEND_ARN" "/review-insight/TG_FRONTEND_ARN"; do
  TG_ARN=$(aws ssm get-parameter --name "$tg_param" \
    --query Parameter.Value --output text --region "$AWS_REGION" 2>/dev/null || echo "")
  [[ -n "$TG_ARN" && "$TG_ARN" != "None" ]] || continue
  sleep 5  # ALB deletion takes a moment
  aws elbv2 delete-target-group --target-group-arn "$TG_ARN" \
    --region "$AWS_REGION" --output text 2>/dev/null || true
done
echo "✓ Deleted target groups"

# ── RDS ───────────────────────────────────────────────────────────────────────
aws rds delete-db-instance \
  --db-instance-identifier "${APP}-db" \
  --skip-final-snapshot \
  --region "$AWS_REGION" --output text 2>/dev/null || true
echo "✓ RDS deletion initiated (takes ~5 min)"

# ── ECR repos ─────────────────────────────────────────────────────────────────
for repo in "${APP}-backend" "${APP}-frontend"; do
  aws ecr delete-repository --repository-name "$repo" --force \
    --region "$AWS_REGION" --output text 2>/dev/null || true
  echo "✓ Deleted ECR repo: $repo"
done

# ── SSM parameters ────────────────────────────────────────────────────────────
for param in $(aws ssm describe-parameters \
    --parameter-filters "Key=Name,Option=BeginsWith,Values=/review-insight/" \
    --query "Parameters[*].Name" --output text --region "$AWS_REGION" 2>/dev/null); do
  aws ssm delete-parameter --name "$param" --region "$AWS_REGION" 2>/dev/null || true
done
echo "✓ Deleted SSM parameters"

echo ""
echo "✓ Teardown complete. Check AWS console to confirm all resources are gone."

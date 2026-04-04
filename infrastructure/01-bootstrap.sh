#!/usr/bin/env bash
# Step 1 — ECR repos + IAM task-execution role.
# Run once. Safe to re-run (idempotent).
set -euo pipefail
source "$(dirname "$0")/config.sh"

# ── ECR repos ─────────────────────────────────────────────────────────────────
for REPO in "${APP}-backend" "${APP}-frontend"; do
  if aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" &>/dev/null; then
    echo "✓ ECR repo already exists: $REPO"
  else
    aws ecr create-repository \
      --repository-name "$REPO" \
      --image-scanning-configuration scanOnPush=true \
      --region "$AWS_REGION" \
      --output table
    echo "✓ Created ECR repo: $REPO"
  fi
done

# ── ECS Task Execution Role ───────────────────────────────────────────────────
ROLE_NAME="ecsTaskExecutionRole"

if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
  echo "✓ IAM role already exists: $ROLE_NAME"
else
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' --output table

  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

  # Allow reading SSM secrets (for DB URL, API keys)
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess

  echo "✓ Created IAM role: $ROLE_NAME"
fi

# ── Put secrets into SSM Parameter Store ─────────────────────────────────────
# You'll be prompted to enter each value. They are stored encrypted.
echo ""
echo "── Storing secrets in SSM Parameter Store ──────────────────────────────"
echo "(press ENTER to skip a secret that's already set)"
echo ""

put_secret() {
  local path=$1
  local label=$2
  read -rsp "Enter ${label} (hidden): " val
  echo ""
  if [[ -n "$val" ]]; then
    aws ssm put-parameter \
      --name "$path" \
      --value "$val" \
      --type SecureString \
      --overwrite \
      --region "$AWS_REGION" \
      --output text
    echo "✓ Stored: $path"
  else
    echo "  Skipped: $path"
  fi
}

put_secret "$SSM_DATABASE_URL"    "DATABASE_URL (postgresql://user:pass@host:5432/db)"
put_secret "$SSM_OPENAI_KEY"      "OPENAI_API_KEY"
put_secret "$SSM_OUTSCRAPER_KEY"  "OUTSCRAPER_API_KEY"
put_secret "$SSM_JWT_SECRET"      "JWT_SECRET_KEY"

echo ""
echo "✓ Bootstrap complete. Next: run 02-rds.sh or skip if using an existing database."

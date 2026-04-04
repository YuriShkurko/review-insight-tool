#!/usr/bin/env bash
# Step 2 — RDS PostgreSQL (db.t3.micro, free tier eligible for 12 months).
# Skip this if you're keeping Railway's DB — just point DATABASE_URL at it.
# Safe to re-run.
set -euo pipefail
source "$(dirname "$0")/config.sh"

DB_INSTANCE_ID="${APP}-db"
DB_NAME="review_insight"
DB_USER="postgres"
DB_PORT=5432

# Generate a password if not already set
DB_PASS=$(aws ssm get-parameter \
  --name "/review-insight/RDS_PASSWORD" \
  --with-decryption \
  --query Parameter.Value \
  --output text 2>/dev/null || echo "")

if [[ -z "$DB_PASS" ]]; then
  DB_PASS=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)
  aws ssm put-parameter \
    --name "/review-insight/RDS_PASSWORD" \
    --value "$DB_PASS" \
    --type SecureString \
    --region "$AWS_REGION" \
    --output text
  echo "✓ Generated and stored RDS password"
fi

# Check if DB already exists
if aws rds describe-db-instances \
     --db-instance-identifier "$DB_INSTANCE_ID" \
     --region "$AWS_REGION" &>/dev/null; then
  echo "✓ RDS instance already exists: $DB_INSTANCE_ID"
else
  echo "Creating RDS instance (takes ~5 min)..."
  aws rds create-db-instance \
    --db-instance-identifier "$DB_INSTANCE_ID" \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version "16" \
    --master-username "$DB_USER" \
    --master-user-password "$DB_PASS" \
    --db-name "$DB_NAME" \
    --allocated-storage 20 \
    --storage-type gp2 \
    --no-multi-az \
    --publicly-accessible \
    --backup-retention-period 7 \
    --region "$AWS_REGION" \
    --output table

  echo "Waiting for RDS to become available..."
  aws rds wait db-instance-available \
    --db-instance-identifier "$DB_INSTANCE_ID" \
    --region "$AWS_REGION"
fi

# Get endpoint and write full DATABASE_URL to SSM
ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE_ID" \
  --query "DBInstances[0].Endpoint.Address" \
  --output text \
  --region "$AWS_REGION")

DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${ENDPOINT}:${DB_PORT}/${DB_NAME}"
aws ssm put-parameter \
  --name "$SSM_DATABASE_URL" \
  --value "$DATABASE_URL" \
  --type SecureString \
  --overwrite \
  --region "$AWS_REGION" \
  --output text

echo ""
echo "✓ RDS ready: $ENDPOINT"
echo "✓ DATABASE_URL saved to SSM: $SSM_DATABASE_URL"
echo ""
echo "Next: run 03-network.sh"

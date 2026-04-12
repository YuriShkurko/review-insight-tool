#!/usr/bin/env bash
# Shared config — source this in every other script.
# Edit AWS_REGION to your preferred region before running anything.
set -euo pipefail

# ── You must set these ────────────────────────────────────────────────────────
export AWS_REGION="${AWS_REGION:-eu-central-1}"   # Frankfurt (closest to IL)

# Auto-detected from your AWS CLI credentials
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ── Fixed names (no need to change) ──────────────────────────────────────────
export APP="review-insight"
export ECS_CLUSTER="${APP}"
export ECR_BACKEND="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP}-backend"
export ECR_FRONTEND="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${APP}-frontend"

# SSM paths where secrets live (set these via AWS console or CLI, never in code)
export SSM_DATABASE_URL="/review-insight/DATABASE_URL"
export SSM_OPENAI_KEY="/review-insight/OPENAI_API_KEY"
export SSM_OUTSCRAPER_KEY="/review-insight/OUTSCRAPER_API_KEY"
export SSM_JWT_SECRET="/review-insight/JWT_SECRET_KEY"
export SSM_MONGO_URI="/review-insight/MONGO_URI"

echo "✓ Config loaded (account=${AWS_ACCOUNT_ID}, region=${AWS_REGION})"

#!/usr/bin/env bash
# Step 4 — Application Load Balancer + target groups + optional SSL.
#
# HTTP-only (default):
#   port 80  → /api/* → backend:8000
#            → /*     → frontend:3000
#
# With SSL (pass CERTIFICATE_ARN):
#   port 80  → redirect to HTTPS (301)
#   port 443 → /api/* → backend:8000
#            → /*     → frontend:3000
#
# Usage:
#   bash infrastructure/04-alb.sh                              # HTTP-only
#   CERTIFICATE_ARN=arn:aws:acm:... bash infrastructure/04-alb.sh  # HTTPS
#
# The ACM certificate must already exist and be validated before running.
# Safe to re-run (idempotent). Re-running with CERTIFICATE_ARN on an
# existing HTTP-only ALB upgrades it: HTTP rules are removed and the
# listener becomes a redirect; HTTPS listener is created with routing.
set -euo pipefail
source "$(dirname "$0")/config.sh"

# Optional: ACM certificate ARN. Leave unset for HTTP-only.
CERTIFICATE_ARN="${CERTIFICATE_ARN:-}"

# ── Fetch values stored by 03-network.sh ─────────────────────────────────────
VPC_ID=$(aws ssm get-parameter --name "/review-insight/VPC_ID" \
  --query Parameter.Value --output text --region "$AWS_REGION")
SG_ALB_ID=$(aws ssm get-parameter --name "/review-insight/SG_ALB_ID" \
  --query Parameter.Value --output text --region "$AWS_REGION")

# Get default subnets (ALB requires at least 2 AZs)
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
    echo "✓ Created target group: $name → $arn" >&2
  else
    echo "✓ Target group already exists: $name" >&2
  fi
  echo "$arn"
}

TG_BACKEND_ARN=$(create_tg "${APP}-backend" 8000 "/api/health")
TG_FRONTEND_ARN=$(create_tg "${APP}-frontend" 3000 "/")

# ── HTTP listener (port 80) ───────────────────────────────────────────────────
HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn "$ALB_ARN" \
  --query "Listeners[?Port==\`80\`].ListenerArn" \
  --output text --region "$AWS_REGION" 2>/dev/null || echo "")

if [[ -z "$HTTP_LISTENER_ARN" || "$HTTP_LISTENER_ARN" == "None" ]]; then
  if [[ -n "$CERTIFICATE_ARN" ]]; then
    # SSL mode: create HTTP listener as redirect — no routing rules needed
    HTTP_LISTENER_ARN=$(aws elbv2 create-listener \
      --load-balancer-arn "$ALB_ARN" \
      --protocol HTTP --port 80 \
      --default-actions "Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}" \
      --region "$AWS_REGION" \
      --query "Listeners[0].ListenerArn" --output text)
    echo "✓ Created HTTP listener (redirect → HTTPS): $HTTP_LISTENER_ARN"
  else
    # HTTP-only mode: forward to frontend, /api/* rule for backend
    HTTP_LISTENER_ARN=$(aws elbv2 create-listener \
      --load-balancer-arn "$ALB_ARN" \
      --protocol HTTP --port 80 \
      --default-actions "Type=forward,TargetGroupArn=${TG_FRONTEND_ARN}" \
      --region "$AWS_REGION" \
      --query "Listeners[0].ListenerArn" --output text)
    echo "✓ Created HTTP listener (forward to frontend): $HTTP_LISTENER_ARN"

    aws elbv2 create-rule \
      --listener-arn "$HTTP_LISTENER_ARN" \
      --priority 10 \
      --conditions "Field=path-pattern,Values='/api/*'" \
      --actions "Type=forward,TargetGroupArn=${TG_BACKEND_ARN}" \
      --region "$AWS_REGION" --output table
    echo "✓ Created routing rule: /api/* → backend (HTTP)"
  fi
else
  echo "✓ HTTP listener already exists: $HTTP_LISTENER_ARN"

  if [[ -n "$CERTIFICATE_ARN" ]]; then
    # Upgrade path: remove non-default rules then switch listener to redirect.
    # (Rules on an HTTP redirect listener are redundant — all traffic goes to HTTPS.)
    NON_DEFAULT_RULES=$(aws elbv2 describe-rules \
      --listener-arn "$HTTP_LISTENER_ARN" \
      --query "Rules[?IsDefault==\`false\`].RuleArn" \
      --output text --region "$AWS_REGION")
    for rule_arn in $NON_DEFAULT_RULES; do
      [[ -z "$rule_arn" ]] && continue
      aws elbv2 delete-rule --rule-arn "$rule_arn" --region "$AWS_REGION" --output text
      echo "✓ Removed HTTP listener rule: $rule_arn"
    done

    aws elbv2 modify-listener \
      --listener-arn "$HTTP_LISTENER_ARN" \
      --default-actions "Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,StatusCode=HTTP_301}" \
      --region "$AWS_REGION" --output text
    echo "✓ HTTP listener updated: forward → redirect to HTTPS"
  fi
fi

# ── HTTPS listener (port 443) — only when CERTIFICATE_ARN is provided ─────────
if [[ -n "$CERTIFICATE_ARN" ]]; then
  HTTPS_LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn "$ALB_ARN" \
    --query "Listeners[?Port==\`443\`].ListenerArn" \
    --output text --region "$AWS_REGION" 2>/dev/null || echo "")

  if [[ -z "$HTTPS_LISTENER_ARN" || "$HTTPS_LISTENER_ARN" == "None" ]]; then
    HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
      --load-balancer-arn "$ALB_ARN" \
      --protocol HTTPS --port 443 \
      --certificates "CertificateArn=${CERTIFICATE_ARN}" \
      --default-actions "Type=forward,TargetGroupArn=${TG_FRONTEND_ARN}" \
      --region "$AWS_REGION" \
      --query "Listeners[0].ListenerArn" --output text)
    echo "✓ Created HTTPS listener: $HTTPS_LISTENER_ARN"

    aws elbv2 create-rule \
      --listener-arn "$HTTPS_LISTENER_ARN" \
      --priority 10 \
      --conditions "Field=path-pattern,Values='/api/*'" \
      --actions "Type=forward,TargetGroupArn=${TG_BACKEND_ARN}" \
      --region "$AWS_REGION" --output table
    echo "✓ Created routing rule: /api/* → backend (HTTPS)"
  else
    echo "✓ HTTPS listener already exists: $HTTPS_LISTENER_ARN"
  fi

  aws ssm put-parameter --name "/review-insight/CERTIFICATE_ARN" --value "$CERTIFICATE_ARN" \
    --type String --overwrite --region "$AWS_REGION" --output text
  echo "✓ Saved CERTIFICATE_ARN to SSM"
else
  echo "⚠  CERTIFICATE_ARN not set — running HTTP-only."
  echo "   To add SSL: CERTIFICATE_ARN=arn:aws:acm:... bash infrastructure/04-alb.sh"
fi

# ── Save outputs to SSM ───────────────────────────────────────────────────────
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
if [[ -n "$CERTIFICATE_ARN" ]]; then
  echo "  ALB DNS (use as CNAME target): $ALB_DNS"
  echo "  Public URL: https://<your-domain>  (after DNS propagates)"
  echo ""
  echo "⚠  Set BACKEND_PUBLIC_URL=https://<your-domain> in GitHub vars for the frontend build."
else
  echo "  Public URL: http://${ALB_DNS}"
  echo ""
  echo "⚠  Set BACKEND_PUBLIC_URL=http://${ALB_DNS} in GitHub vars for the frontend build."
fi
echo "Next: run 05-ecs.sh"

# AWS Deployment — Review Insight Tool

Deploys the full stack to **AWS ECS Fargate** behind an Application Load Balancer.
Database: **RDS PostgreSQL** (or keep Railway's DB — your choice).

```
Internet → ALB:443 (HTTPS) → /api/* → ECS Fargate (backend:8000)
                            → /*     → ECS Fargate (frontend:3000)
                                          ↕
                                      RDS PostgreSQL
         ALB:80  (HTTP)   → redirect to HTTPS (301)
```

> **HTTP-only fallback:** if no ACM certificate is configured, port 80 routes directly
> to the services. See [Step 2b — SSL](#step-2b--ssl-optional) to add HTTPS later.

---

## Prerequisites

| Tool | Install |
|------|---------|
| AWS CLI v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| Docker | https://docs.docker.com/get-docker/ |
| `jq` | `choco install jq` / `brew install jq` / `apt install jq` |

**Run scripts in Git Bash or WSL** (not PowerShell — these are bash scripts).

---

## Step 0 — AWS Account Setup (one-time, you do this)

1. Create an AWS account at https://aws.amazon.com
2. Go to **IAM → Users → Create user** (`ci-deploy`)
3. Attach policy: `AdministratorAccess` (tighten later)
4. Create **Access Key** → save `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
5. Run `aws configure` and enter those keys

---

## Step 1 — Configure your region

Edit `infrastructure/config.sh`:

```bash
export AWS_REGION="eu-central-1"   # Frankfurt (recommended for Israel)
# Other options: eu-west-1 (Ireland), me-south-1 (Bahrain)
```

---

## Step 2 — One-time infrastructure setup

Run these scripts **in order** from the repo root using Git Bash / WSL:

```bash
# 1. ECR repos + IAM role + store secrets in SSM
bash infrastructure/01-bootstrap.sh

# 2. RDS PostgreSQL (skip if keeping Railway DB)
bash infrastructure/02-rds.sh

# 3. Security groups (uses default VPC)
bash infrastructure/03-network.sh

# 4. Application Load Balancer + routing rules (HTTP-only)
bash infrastructure/04-alb.sh

# 5. ECS cluster + task definitions + services
#    (needs images in ECR first — see step 3 below)
bash infrastructure/05-ecs.sh
```

Each script is **idempotent** — safe to re-run if something fails halfway.

---

## Step 2b — SSL (optional)

Adds HTTPS via a free **AWS ACM public certificate**. Requires a custom domain you control.

**Prerequisites:** a domain with DNS access (e.g. Route 53, Cloudflare, Namecheap).

```bash
# 1. Request a public certificate (free) in ACM
aws acm request-certificate \
  --domain-name "yourdomain.com" \
  --subject-alternative-names "www.yourdomain.com" \
  --validation-method DNS \
  --region "$AWS_REGION"
# → copy the CertificateArn from the output

# 2. Validate via DNS — ACM shows a CNAME record to add to your DNS provider.
#    Check status until it says "ISSUED" (usually 1-5 minutes after DNS propagates):
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:REGION:ACCOUNT:certificate/... \
  --region "$AWS_REGION" \
  --query "Certificate.Status"

# 3. Run 04-alb.sh with the certificate ARN — upgrades HTTP-only to HTTPS.
#    Safe to re-run; existing HTTP rules are removed and replaced with a redirect.
CERTIFICATE_ARN=arn:aws:acm:REGION:ACCOUNT:certificate/... \
  bash infrastructure/04-alb.sh

# 4. Point your domain at the ALB — add a CNAME (or Alias for Route 53):
#    CNAME  yourdomain.com  →  <alb-dns-name>.elb.amazonaws.com
```

After DNS propagates, `https://yourdomain.com` and `https://yourdomain.com/api/*` will work.
Update `BACKEND_PUBLIC_URL` in GitHub vars to `https://yourdomain.com` (see Step 3 below).

---

## Step 3 — GitHub Secrets + Variables

Go to your GitHub repo → **Settings → Secrets and variables → Actions**.

### Secrets (sensitive — never commit these)
| Name | Value |
|------|-------|
| `AWS_ACCESS_KEY_ID` | From IAM user step 0 |
| `AWS_SECRET_ACCESS_KEY` | From IAM user step 0 |

### Variables (non-sensitive)
| Name | Value | Where to find it |
|------|-------|-----------------|
| `AWS_REGION` | `eu-central-1` | your choice |
| `AWS_ACCOUNT_ID` | 12-digit AWS account ID | `aws sts get-caller-identity` |
| `BACKEND_PUBLIC_URL` | `https://yourdomain.com` (SSL) or `http://<alb-dns>` (HTTP-only) | output of `04-alb.sh` |

---

## Step 4 — First deploy

Push to `main` — the CD workflow in `.github/workflows/cd.yml` will:

1. Lint + type-check the code
2. Build backend Docker image → push to ECR
3. Build frontend Docker image (with `NEXT_PUBLIC_API_URL` baked in) → push to ECR
4. Register new ECS task definition revisions
5. Update both ECS services
6. Wait for services to stabilize
7. Print the public URL

---

## Cost Estimate

| Resource | Tier | Monthly cost |
|----------|------|-------------|
| ECS Fargate (backend 0.5 vCPU, 1GB) | always-on | ~$15 |
| ECS Fargate (frontend 0.25 vCPU, 0.5GB) | always-on | ~$8 |
| RDS PostgreSQL db.t3.micro | always-on | ~$15 (free first 12 months) |
| ALB | per LCU | ~$5–8 |
| ECR storage | <1GB | ~$0.10 |
| **Total** | | **~$25–45/month** |

**Cost saving options:**
- Use Railway's existing Postgres instead of RDS (saves $15/month)
- Scale ECS desired count to 0 when not using it:
  ```bash
  aws ecs update-service --cluster review-insight \
    --service review-insight-backend --desired-count 0 --region eu-central-1
  ```

---

## Teardown (stop all billing)

```bash
bash infrastructure/teardown.sh
```

Prompts for confirmation. Deletes ECS, ALB, ECR repos, RDS. SSM parameters cleaned up too.

---

## Useful commands

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster review-insight \
  --services review-insight-backend review-insight-frontend \
  --region eu-central-1 \
  --query 'services[*].{name:serviceName,running:runningCount,status:status}'

# View backend logs (last 100 lines)
aws logs tail /ecs/review-insight-backend --follow --region eu-central-1

# View frontend logs
aws logs tail /ecs/review-insight-frontend --follow --region eu-central-1

# Force a new deployment (e.g. after config change)
aws ecs update-service --cluster review-insight \
  --service review-insight-backend --force-new-deployment --region eu-central-1

# Scale down to zero (pause billing)
aws ecs update-service --cluster review-insight \
  --service review-insight-backend --desired-count 0 --region eu-central-1
aws ecs update-service --cluster review-insight \
  --service review-insight-frontend --desired-count 0 --region eu-central-1
```

---

## Architecture

```
GitHub Actions (push to main)
    │
    ├── lint + typecheck
    ├── docker build backend  → ECR
    ├── docker build frontend → ECR (NEXT_PUBLIC_API_URL baked in)
    └── aws ecs update-service
                │
                ▼
        ECS Fargate Cluster
        ┌─────────────────┐     ┌──────────────────┐
        │ backend:8000    │────▶│ RDS PostgreSQL   │
        │ (FastAPI)       │     │ (db.t3.micro)    │
        └─────────────────┘     └──────────────────┘
        ┌─────────────────┐
        │ frontend:3000   │
        │ (Next.js)       │
        └─────────────────┘
                │
        ALB :443 HTTPS          ALB :80 HTTP
          /api/* → backend       redirect → HTTPS
          /*     → frontend
                │
              Internet (https://yourdomain.com)
```

Secrets live in **AWS SSM Parameter Store** (SecureString) — never in env vars committed to git.

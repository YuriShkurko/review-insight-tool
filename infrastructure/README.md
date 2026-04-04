# AWS Deployment — Review Insight Tool

Deploys the full stack to **AWS ECS Fargate** behind an Application Load Balancer.
Database: **RDS PostgreSQL** (or keep Railway's DB — your choice).

```
Internet → ALB → /api/* → ECS Fargate (backend:8000)
                → /*     → ECS Fargate (frontend:3000)
                              ↕
                          RDS PostgreSQL
```

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

# 4. Application Load Balancer + routing rules
bash infrastructure/04-alb.sh

# 5. ECS cluster + task definitions + services
#    (needs images in ECR first — see step 3 below)
bash infrastructure/05-ecs.sh
```

Each script is **idempotent** — safe to re-run if something fails halfway.

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
| `BACKEND_PUBLIC_URL` | `http://<alb-dns-name>` | output of `04-alb.sh` |

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
        ALB (port 80)
          /api/* → backend
          /*     → frontend
                │
              Internet
```

Secrets live in **AWS SSM Parameter Store** (SecureString) — never in env vars committed to git.

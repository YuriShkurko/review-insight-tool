# v2.10.0 — AWS ECS deployment + CD pipeline

## What's New

### AWS ECS Fargate deployment
- Full production deployment on **AWS ECS Fargate** behind an Application Load Balancer.
  Both the backend (FastAPI) and frontend (Next.js) run as separate Fargate services in
  the `review-insight` ECS cluster (`eu-central-1`).
- Traffic routing via ALB: `/api/*` → backend (port 8000), `/*` → frontend (port 3000).
- Secrets (DATABASE_URL, OPENAI_API_KEY, OUTSCRAPER_API_KEY, JWT_SECRET_KEY) stored as
  `SecureString` in AWS SSM Parameter Store — injected at container startup, never in
  code or environment files.
- Database: existing Railway PostgreSQL instance reused via external connection URL
  (saves ~$15/month vs provisioning RDS).

### GitHub Actions CD pipeline (`.github/workflows/cd.yml`)
- Triggered on every push to `main`.
- Runs a quick lint + TypeScript guard before building images.
- Builds backend and frontend Docker images tagged with the commit SHA.
- Pushes both images to private ECR repositories
  (`review-insight-backend`, `review-insight-frontend`).
- `NEXT_PUBLIC_API_URL` is baked into the frontend image at build time from
  the `BACKEND_PUBLIC_URL` GitHub variable.
- Registers a new ECS task definition revision per service with the exact SHA-tagged
  image, then updates each service and waits for stability.
- Prints the public ALB URL as a workflow notice on every successful deploy.
- Uses `concurrency` group to cancel stale queued runs on fast-push workflows.

### Infrastructure scripts (`infrastructure/`)
- `config.sh` — shared variables (region, ECR URIs, SSM paths); single place to change
  the target region.
- `01-bootstrap.sh` — ECR repos + `ecsTaskExecutionRole` IAM role + interactive SSM
  secret storage.
- `02-rds.sh` — optional RDS PostgreSQL setup (skipped; Railway DB reused).
- `03-network.sh` — security groups: ALB open to internet, ECS tasks only reachable
  from ALB.
- `04-alb.sh` — Application Load Balancer, target groups, HTTP listener, path-based
  routing rule.
- `05-ecs.sh` — ECS cluster, task definitions, and Fargate services.
- `teardown.sh` — deletes all AWS resources (ECS, ALB, ECR, RDS, SSM) with confirmation
  prompt; safe cost-control escape hatch.

### Makefile helpers
- `make aws-bootstrap`, `make aws-rds`, `make aws-network`, `make aws-alb`,
  `make aws-ecs` — run each infrastructure setup step.
- `make aws-status` — show running/desired counts for both ECS services.
- `make aws-logs-backend`, `make aws-logs-frontend` — tail CloudWatch log streams.
- `make aws-teardown` — delete all AWS infrastructure.

## Upgrade Notes

- Requires AWS CLI v2 installed and `aws configure` run with a `ci-deploy` IAM user
  (`AdministratorAccess`).
- Add two GitHub **Secrets**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.
- Add three GitHub **Variables**: `AWS_REGION`, `AWS_ACCOUNT_ID`, `BACKEND_PUBLIC_URL`.
- Infrastructure must be provisioned before the first push (scripts `01` → `05`).
- See `infrastructure/README.md` for the full step-by-step guide.

## Breaking Changes

None. Railway deployment continues to work unchanged; AWS is an additive target.

## Full Changelog

v2.9.2...v2.10.0

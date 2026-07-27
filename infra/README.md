# Infrastructure (Terraform)

Deploys ProvenanceAgent to AWS: **API Gateway (HTTPS) → ALB → ECS Fargate**,
image in **ECR**, secrets in **Secrets Manager**, logs/metrics in **CloudWatch**,
inside the account's **default VPC** (no NAT Gateway). A **$20 budget alarm**
guards against runaway cost.

```
Client ─HTTPS→ API Gateway ─HTTP→ ALB ─→ ECS Fargate (FastAPI)
                                            │ secrets at boot
                                       Secrets Manager
                                            │
                        Neo4j Aura + Qdrant Cloud (managed) + OpenAI
```

## Prerequisites
- `aws configure` done (region `eu-central-1`), Terraform ≥ 1.6, Docker running.
- `terraform.tfvars` present (gitignored) with the app secrets — see
  `terraform.tfvars.example`.

## Deploy (first time)

The ECS service needs an image to pull, so create the registry first, push, then
apply the rest:

```bash
cd infra
terraform init
terraform apply -target=aws_ecr_repository.app        # 1. create ECR only

# 2. build + push the image
REPO=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS --password-stdin "${REPO%/*}"
docker build -f ../docker/Dockerfile -t "$REPO:latest" ..
docker push "$REPO:latest"

terraform apply                                        # 3. create the rest
terraform output api_url                               # your public HTTPS endpoint
```

## Call it
```bash
API=$(terraform output -raw api_url)
curl "$API/health"
curl -X POST "$API/v1/query" -H "X-API-Key: <your api_keys value>" \
  -H "Content-Type: application/json" \
  -d '{"question":"What nationality is the director of Nemesis 2: Nebula?"}'
```

## Redeploy a new image
```bash
docker build -f ../docker/Dockerfile -t "$REPO:latest" .. && docker push "$REPO:latest"
aws ecs update-service --cluster provenance-agent --service provenance-agent \
  --force-new-deployment --region eu-central-1
```

## Tear down (stop all charges)
```bash
terraform destroy
```

## Notes
- **State** is local (`terraform.tfstate`, gitignored — it contains secrets).
  Production upgrade: S3 backend + DynamoDB lock.
- The ALB is internet-facing (HTTP) as well as fronted by API Gateway; to fully
  hide it, put it in private subnets behind a VPC Link (more setup).
- Switch `launch_type` to `FARGATE_SPOT` in `ecs.tf` to cut compute cost ~70%.

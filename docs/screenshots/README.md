# Screenshots — capture manifest

Save each file with the **exact filename** below and it will render automatically
in the main [`README.md`](../../README.md). Capture the AWS ones **before
`terraform destroy`** — they die with the stack.

| Save as (exact name)          | What to capture | Where |
| ----------------------------- | --------------- | ----- |
| `demo.gif`                    | Terminal: 401 without key, then a `route:"both"` query returning a cited, grounded answer + trace. Warm the container first; use `jq`. | Local terminal (see main README → Demo) |
| `langfuse-trace.png`          | One `/v1/query` trace expanded to the node tree (redact → supervisor → graph+vector → synthesis → grader) with per-node tokens/latency/cost | https://cloud.langfuse.com → project → Traces |
| `cloudwatch-dashboard.png`    | The dashboard: p50/p95/p99 latency, requests, errors | https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#dashboards/dashboard/provenance-agent |
| `github-actions-deploy.png`   | The green deploy run — all steps ✅ (OIDC, ECR push, ECS roll) | https://github.com/munyaradzi-zhou/provenance-agent/actions/workflows/deploy.yml (run 30333711767) |
| `ecs-service.png`             | ECS service: 1 task RUNNING, healthy | https://eu-central-1.console.aws.amazon.com/ecs/v2/clusters/provenance-agent/services/provenance-agent/health?region=eu-central-1 |

### Optional extras (not embedded, but nice to keep)

| Save as                    | What | Where |
| -------------------------- | ---- | ----- |
| `api-gateway-health.png`   | Browser showing `{"status":"ok"}` at the HTTPS `/health` URL | https://79075o8z5f.execute-api.eu-central-1.amazonaws.com/health |
| `ecr-images.png`           | ECR repo with `:latest` + git-SHA tags pushed by CI | https://eu-central-1.console.aws.amazon.com/ecr/repositories/private/287530975293/provenance-agent?region=eu-central-1 |

**Tips:** large terminal font (~16–18pt); keep the GIF < ~30s and a few MB so it
renders inline; [ScreenToGif](https://www.screentogif.com/) is the easiest
Windows recorder.

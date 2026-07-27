# ProvenanceAgent — Zero-to-Deployment Execution Plan

A complete technical checklist to take this repo from its current **stubbed
scaffold** to a **live, monitored, evaluated, production-deployed multi-agent
RAG service on AWS** — 100% of the flagship described in `PORTFOLIO_PLAN.md`.

This plan is the single source of truth for *what remains*. Work top to bottom.
Each phase has concrete tasks (with file paths), a **Definition of Done**, and
the exact command/artifact that proves it.

---

## 0. Where the project stands today (baseline audit)

| Area | Status | Reality |
|------|--------|---------|
| LangGraph structure | 🟡 skeleton | Nodes + conditional routing exist; all logic is stubbed |
| Supervisor routing | 🔴 stub | Heuristic `"both" if "?" in q else "vector"` — not an LLM |
| Graph retrieval (Neo4j) | 🔴 stub | Returns `"[graph-context stub for: ...]"`; no driver, no Cypher |
| Vector retrieval (Qdrant) | 🔴 stub | Returns a stub string; no embeddings, no client |
| Synthesis | 🔴 stub | String concat, no LLM, `faithfulness=None` |
| Data ingestion | 🔴 missing | Nothing populates Neo4j or Qdrant — no corpus exists |
| PII redaction | 🟡 partial | Regex email/phone only; plan calls for Presidio |
| FastAPI service | 🟡 partial | `/health` + `/query` work; no auth, rate-limit, error handling, versioning |
| Evaluation (RAGAS) | 🔴 stub | Loads `eval_set.jsonl`; does not run RAGAS; not gating CI |
| Observability (Langfuse) | 🔴 missing | Config keys exist; no tracing wired |
| MLOps (MLflow / DVC) | 🔴 missing | In requirements only; no runs, no versioned artifacts |
| AWS deployment | 🔴 missing | No IaC, no ECR, no ECS, no ALB, no API Gateway |
| CI/CD | 🟡 partial | pytest runs; eval gate commented out; no build/push/deploy |
| Tests | 🟡 minimal | 2 smoke tests pass; no unit/integration/contract coverage |
| Git | 🔴 missing | **Not a git repository yet** |
| README results | 🔴 TBD | All metrics are placeholders |

**Verified working now:** `pytest -q` → 2 passed; deps import cleanly in `venv`.

**Guiding principles**
- Ship a thin vertical slice end-to-end *first*, then deepen each layer.
- Every stub is replaced behind its existing interface — no restructuring needed.
- Keep it runnable locally (`docker compose up`) at every commit.
- Cost discipline: default to `gpt-4o-mini` + small embeddings; AWS on Fargate spot / scale-to-zero where possible.

---

## Phase 0 — Foundations & repo hygiene (½ day)

Before writing feature code, make the repo a real, gated project.

- [x] `git init`, set default branch `main`, first commit of current scaffold.
- [x] Create GitHub repo, push (chose **private** now, flip to public later). Topics: TODO on flip.
- [~] Branch protection on `main` — **deferred**: GitHub Free blocks branch protection on *private* repos (HTTP 403). Auto-enable on the public flip. CI still runs on every push.
- [x] Split `requirements.txt` (lean runtime) → + `requirements-dev.txt` (ruff, mypy, pre-commit, pytest, ragas, mlflow, dvc). (Exact pinning / `uv` lockfile = later reproducibility upgrade.)
- [x] Add **`ruff`** (lint + format) + **`mypy`** (type-check) + **`pre-commit`** hooks. mypy is CI-only (isolated pre-commit env lacks real deps + slow); pre-commit trimmed to native ruff hooks for speed on Windows.
- [x] Add `pyproject.toml` with tool config (ruff, mypy, pytest markers).
- [x] Add `tasks.ps1` (Windows) + `Makefile` (Linux/CI): `fmt lint type test check run up down seed eval`.
- [x] Wire ruff + mypy + pytest into `.github/workflows/ci.yml` as separate jobs (all green).
- [x] Add `.gitattributes` to normalize line endings to LF (Windows dev + Linux CI).

**Definition of Done:** fresh clone → `make lint type test` all green in CI. ✅ (branch protection pends public flip.)

---

## Phase 1 — Agentic core: real LangGraph (weeks 1–2)

Replace stub logic with a genuine supervisor/worker multi-agent graph. Keep the
existing node signatures in `app/agents/graph.py`.

### 1.1 LLM-driven supervisor router
- [ ] In `supervisor_node`, call the LLM (structured output) to classify each question → `graph` | `vector` | `both`, with a one-line justification appended to `trace`.
- [ ] Use `langchain-openai` with a Pydantic `RouteDecision` schema (`.with_structured_output`).
- [ ] Add a deterministic fallback (current heuristic) when the LLM call fails, so the graph never hard-fails on routing.

### 1.2 Real synthesis agent
- [ ] `synthesis_node`: LLM prompt over `graph_context` + `vector_context` → grounded answer that **cites which source** each claim came from.
- [ ] Store the prompt template in `app/agents/prompts/` (versioned, DVC-tracked in Phase 5).
- [ ] Return a structured answer object (answer text + citations list) in state.

### 1.3 Robustness: retry / repair edges (the "agentic" differentiator)
- [ ] Add a **grader/critic node** after synthesis that checks the answer is grounded in retrieved context (LLM-as-judge, cheap model).
- [ ] Add a **conditional repair edge**: if grader flags ungrounded/empty → loop back to supervisor with a "retrieve more / switch route" signal (bounded by `max_retries` in state to prevent infinite loops).
- [ ] Add `retries: int` to `AgentState`; increment and cap.

### 1.4 Tooling & tests
- [ ] Add unit tests for routing decisions (mock LLM), grader logic, and retry cap.
- [ ] Add a `--visualize` script that dumps the compiled graph to a Mermaid/PNG for the README.

**Definition of Done:** `POST /query` returns a real LLM-synthesised answer with a
non-trivial reasoning trace showing route choice + grader verdict; retry loop
demonstrably fires on a deliberately unanswerable question and terminates.

---

## Phase 2 — Real retrieval + data ingestion (weeks 1–2, parallel)

Nothing is retrievable until a corpus exists. This is the biggest missing piece.

### 2.1 Corpus — 2WikiMultihopQA (chosen ✅, downloaded)
- [x] **Selected `2WikiMultihopQA`** (COLING 2020, Apache-2.0) — the rare benchmark shipping each example with BOTH `evidences` (subject-relation-object triples → Neo4j) AND `context` (Wikipedia paragraphs → Qdrant), plus `answer` + `supporting_facts` (→ RAGAS + reasoning trace). Ideal for proving graph-vs-vector routing.
- [x] Downloaded to `data/raw/` (fixed april7 release): `dev.json` (12,576 ex), `train.json`, `test.json`, `id_aliases.json`. Gitignored; documented in `data/raw/README.md`.
- [x] **Subset** `dev.json` → balanced demo corpus (`app/ingest/subset.py`, 125/type = 500 ex → 3463 passages, 1259 triples, 500 eval Qs in `data/processed/`, gitignored, deterministic/seeded).
- [x] Define the **graph schema** in `docs/schema.md` (`:Entity {name}` nodes, `:REL {name}` edges, Qdrant collection spec, diagrams).

### 2.2 Ingestion pipeline (`app/ingest/`)
- [x] `app/ingest/build_graph.py`: MERGE-based idempotent load of triples into Neo4j (constraint + batched UNWIND).
- [x] `app/ingest/build_vectors.py`: batched embed → upsert passages into Qdrant (collection created with 1536-dim cosine).
- [x] Entry point `python -m app.ingest` (orchestrator; `--graph`/`--vectors`/`--per-type`).
- [~] Tiny seed subset for CI/tests — deferred (integration tests auto-skip without services; revisit when CI gets service containers).

### 2.3 Vector retriever (`app/retrieval/vector.py`)
- [x] Lazy Qdrant client + shared embedder from `Settings`.
- [x] `search()`/`retrieve()`: embed → top-k ANN → formatted context with titles/scores.
- [x] Optional **hybrid re-ranking** behind `rerank_enabled` (over-fetch + lexical-overlap boost).

### 2.4 Graph retriever (`app/retrieval/graph.py`)
- [x] Lazy Neo4j driver from `Settings` + `close()` lifecycle.
- [x] **Text-to-Cypher**: LLM generates Cypher; `is_read_only` injection guard; read session.
- [x] Graceful empty/error handling → deterministic entity-neighbourhood fallback → "" (feeds Phase 1 repair).

### 2.5 Config & tests
- [x] Added `embedding_model`, `embedding_dim`, `top_k`, `rerank_enabled` to `Settings` + `.env.example`.
- [x] Unit tests: Cypher read-only guard (injection cases), subset balance/dedup. Integration tests marked + auto-skip.
- [~] **Flat-vector baseline** path — deferred to Phase 5 (where it's needed for the eval comparison table).
- [x] Agent nodes degrade gracefully on retriever failure (trace-logged).

**Definition of Done:** offline code + gates green ✅. **Live run pending Docker Desktop:**
`docker compose up` → `python -m app.ingest` → a real multi-hop question returns
grounded context; `pytest -m integration` green. ⏳

---

## Phase 3 — Production-grade API (week 3)

Harden the FastAPI service in `app/api/`.

- [ ] **Auth entry layer:** API-key auth (header) on `/query`; keys validated against Secrets Manager value (env locally). This is the "API Gateway + Lambda auth" role, kept simple.
- [ ] **Rate limiting** (per-key) — `slowapi` locally; enforced at API Gateway in AWS.
- [ ] **Structured error handling:** consistent error envelope, request IDs, timeouts on LLM/DB calls, graceful 5xx with trace id.
- [ ] **Request/response models:** version the API (`/v1/query`); add `request_id`, `route_taken`, `latency_ms`, `token_cost` to `QueryOut`.
- [ ] **Health/readiness split:** `/health` (liveness) + `/ready` (checks Neo4j + Qdrant reachable).
- [ ] **CORS** config for the future TS/Next.js client.
- [ ] **Structured JSON logging** (one line per request with route, latency, cost, retrieval-hit) — feeds CloudWatch later.
- [ ] Async where it matters (concurrent graph + vector fan-out).
- [ ] Contract tests for auth failure, rate-limit, malformed input, and the happy path.

**Definition of Done:** unauthenticated request → 401; over-limit → 429; valid
request returns enriched response with `request_id` + latency + cost; `/ready`
reflects dependency health.

---

## Phase 4 — AWS deployment (weeks 3–4)

Target: **ECS Fargate behind an ALB**, images in **ECR**, secrets in **Secrets
Manager**, thin **API Gateway** front door, all defined as code.

### 4.1 Containerisation
- [ ] Multi-stage `docker/Dockerfile` (builder + slim runtime), non-root user, healthcheck, pinned base image digest.
- [ ] `.dockerignore`; verify image size is reasonable.
- [ ] `docker compose up` still brings up api + neo4j + qdrant for local dev.

### 4.2 Infrastructure as Code (`infra/`)
- [ ] Choose **Terraform** (recommended — most transferable) or AWS CDK. Put all infra under `infra/`.
- [ ] **ECR** repository + lifecycle policy.
- [ ] **VPC** (or default), public subnets for ALB, private subnets for tasks, NAT as needed.
- [ ] **ECS Fargate** cluster + service + task definition (CPU/mem sized small); autoscaling target-tracking on CPU; consider Fargate **Spot** for cost.
- [ ] **Application Load Balancer** + target group + `/ready` health check + HTTPS listener (ACM cert).
- [ ] **API Gateway** (HTTP API) in front of ALB for auth + throttling/rate-limits.
- [ ] **Secrets Manager** for `OPENAI_API_KEY`, Neo4j creds, Langfuse keys, API keys; task role reads them at runtime (no secrets in image/env files).
- [ ] **IAM** least-privilege task + execution roles.
- [ ] **Managed data stores decision:** Qdrant self-hosted as a second Fargate service (or Qdrant Cloud free tier); **Neo4j AuraDB free/managed** (avoids running stateful Neo4j on Fargate). Document the choice + cost in `docs/architecture.md`.

### 4.3 Deploy pipeline
- [ ] CI job: on tag/`main`, build image → push to ECR → `terraform apply` (or ECS force-new-deployment) → smoke-test the live `/ready` + `/v1/query`.
- [ ] Configure GitHub → AWS via **OIDC role** (no long-lived AWS keys in CI).
- [ ] Post-deploy job runs one real query against the public endpoint and asserts 200.

### 4.4 Cost guardrails
- [ ] AWS Budget + alarm at a low threshold (e.g. $20/mo).
- [ ] Document a `terraform destroy` teardown path and scale-to-zero option so the demo can be turned off between recruiter viewings.

**Definition of Done:** a **live public HTTPS endpoint** answers a real query;
`architecture diagram` in README matches deployed reality; infra reproducible via
`terraform apply` from clean state.

---

## Phase 5 — MLOps & observability (week 5)

The "un modello in produzione che nessuno guarda è un debito" requirement.

### 5.1 Langfuse tracing
- [ ] Wrap the graph with Langfuse callback/handler so **every `/query` produces a full trace**: each node, model, tokens, latency, cost.
- [ ] Tag traces with `request_id`, route taken, grader verdict, retry count.
- [ ] Verify traces appear in Langfuse cloud; capture a screenshot for the README.

### 5.2 RAGAS eval — real, and gating CI
- [ ] Implement `app/eval/run_eval.py`: run the compiled graph over `eval_set.jsonl`, compute **faithfulness + answer-relevance** (and context-precision/recall) with RAGAS.
- [ ] Expand `eval_set.jsonl` to a meaningful set (~20–40 multi-hop Q/A over the real corpus).
- [ ] Emit a JSON report + human summary; **`sys.exit(1)` if faithfulness < threshold**.
- [ ] Uncomment/enable the RAGAS job in CI so **every commit reports deltas and merges fail on regression**.
- [ ] Run the **flat-vector baseline** through the same eval to produce the "multi-hop accuracy vs flat RAG" number.

### 5.3 MLflow + DVC
- [ ] MLflow: log each eval run as an experiment (params: model, prompt version, top_k; metrics: faithfulness, relevance, latency, cost). Point CI at a tracking store (local file store committed as artifact, or a lightweight remote).
- [ ] DVC: version `data/raw/`, `app/agents/prompts/`, and `eval_set.jsonl`; remote on S3. `dvc repro` reproduces the eval.

### 5.4 CloudWatch metrics
- [ ] Emit custom metrics: p50/p95 latency, token cost per request, retrieval-hit-rate, error rate.
- [ ] Build a CloudWatch dashboard; screenshot for README. Add an alarm on error rate / p95 latency.

**Definition of Done:** a Langfuse trace screenshot, a CI run that **fails on a
seeded faithfulness drop**, an MLflow experiment history, and a CloudWatch
dashboard — all captured as artifacts/screenshots.

---

## Phase 6 — Responsible AI + polish (week 6)

### 6.1 Redaction upgrade
- [ ] Replace regex `app/core/redaction.py` with **Microsoft Presidio** (analyzer + anonymizer) behind the same `redact()` signature; keep regex as fallback.
- [ ] Add PII types: names, locations, credit cards, IBANs, SSN-equivalents.
- [ ] Test redaction on adversarial inputs; add to the OWASP-for-LLM note in docs.
- [ ] Add a brief **threat model / responsible-AI** section (prompt-injection notes on text-to-Cypher, read-only DB guard, PII handling, GDPR posture).

### 6.2 README as a case study
- [ ] Rewrite README: problem → architecture (real diagram) → **filled-in results table** (faithfulness, relevance, p95 latency, avg cost/query, multi-hop vs flat RAG) → cost/latency numbers → "what I'd do next".
- [ ] Ensure `docker compose up` truly works from a clean clone (document required env keys).
- [ ] Add a short **demo GIF** + a **3-minute Loom** walkthrough link.
- [ ] Architecture diagram in draw.io/Excalidraw exported to `docs/`.

### 6.3 GitHub presentation
- [ ] Pin ProvenanceAgent (+ thesis, RetailIQ) on the profile.
- [ ] One-paragraph "what + why" at the top; badges (CI, license).

**Definition of Done:** a recruiter can, in 2 minutes, read what it is, see real
numbers, watch a 3-min demo, and run it locally with one command.

---

## Definition of "100% complete" (acceptance checklist)

- [ ] Live public HTTPS endpoint answers real multi-hop questions with citations + reasoning trace + faithfulness score.
- [ ] Real Neo4j + Qdrant retrieval over an ingested corpus (no stubs anywhere).
- [ ] LLM supervisor routing + grader/retry loop demonstrably working.
- [ ] Deployed on AWS ECS Fargate (ECR, ALB, API Gateway, Secrets Manager) via Terraform.
- [ ] CI: lint + type + tests + **RAGAS eval gate** + build/push/deploy on `main`.
- [ ] Langfuse tracing, MLflow experiment history, DVC-versioned data/prompts, CloudWatch dashboard — all evidenced.
- [ ] Presidio PII redaction + responsible-AI section.
- [ ] README case study with real numbers + demo GIF/Loom; repo pinned.
- [ ] Cost guardrails + documented teardown.

---

## Sequencing & critical path

```
Phase 0 ──▶ Phase 1 (agent core) ──┐
                                    ├──▶ Phase 3 (API) ──▶ Phase 4 (AWS) ──▶ Phase 5 (MLOps) ──▶ Phase 6 (polish)
Phase 0 ──▶ Phase 2 (retrieval) ───┘
```
Phases 1 and 2 run in parallel after foundations. **Phase 2 (data ingestion) is
the highest-risk item** — without a real corpus nothing downstream is meaningful;
start it first. Phase 4 (AWS) is the second risk — budget extra time for IAM/OIDC
and stateful-store decisions.

## Top risks & mitigations
- **No corpus yet** → pick a small provenance dataset in Phase 2 day 1; don't gold-plate ingestion.
- **AWS cost/complexity** → Fargate (not EKS), managed Neo4j Aura + Qdrant Cloud free tiers, budget alarm, teardown script.
- **Text-to-Cypher injection** → constrain to schema, read-only sessions, validate generated Cypher.
- **Flaky LLM eval in CI** → fixed seeds/temperature 0, small eval set, threshold with tolerance band.
- **Scope creep** → the flagship (Phases 0–6) is the deliverable; TS port & fine-tune are separate (below).

---

## Appendix — out-of-scope for *this* repo (separate portfolio projects)

Per `PORTFOLIO_PLAN.md`, after the flagship ships:
- **Weeks 7–8 — Fine-tuning:** LoRA/QLoRA a small open model (Mistral 7B / Llama 3.1 8B) with `peft`+`trl`; HF model card + honest before/after eval.
- **Weeks 9–10 — TypeScript port:** thin LangChain.js orchestration slice + Next.js chat UI over this API, typed end-to-end.

These are tracked separately and do not block ProvenanceAgent reaching 100%.

# Portfolio & Skills Plan — AI Engineer (LLM / Agentic) Roles

Built from 27 live job postings (BMW, spektr, Almawave, Humans.tech, Hermes,
Optimistech, Explore Group, mashfrog, and repeats). Target: AWS, ~25 hrs/week,
closing the **production deployment** and **agentic systems** gaps first.

---

## The core insight

You already own the *AI modeling* half of these postings: RAG, LangChain,
Neo4j, agents, evaluation, end-to-end ML pipelines. What nearly every posting
also demands — and what your portfolio does NOT yet prove — is the
**production / deployment / ops half**:

> "Un modello in produzione che nessuno guarda è un debito, non un asset."
> "It works on my machine doesn't apply to LLMs."
> "Closes the loop from training to serving, doesn't train a prototype and pass the ball."

The plan below is designed so that ONE flagship project closes most of that gap
at once, rather than spreading effort thin.

---

## What the 27 postings actually ask for

**Near-universal (build proof of these):**
- Python, production-grade (clean code, testing, CI/CD)
- LLMs + RAG (embedding, retrieval strategy, re-ranking)
- LangChain / orchestration; multi-agent (LangGraph, AutoGen, CrewAI)
- **AWS** + Docker + Kubernetes
- MLOps: monitoring, drift detection, model versioning (MLflow, DVC)
- LLM evaluation frameworks
- Vector DBs (Qdrant) + graph DBs (Neo4j)

**Frequent (strong differentiators):**
- Agentic / autonomous agents — the 2026 title is literally "Agentic AI Engineer"
- Fine-tuning open LLMs (LLaMA, Mistral)
- TypeScript (core at spektr and Humans.tech)
- Security / responsible AI: PII redaction, GDPR, OWASP for ML

---

## FLAGSHIP PROJECT — "ProvenanceAgent" (weeks 1–6)

A production-deployed, monitored, multi-agent RAG service on AWS. This single
project proves: agentic orchestration, production deployment, AWS, MLOps,
evaluation, AND extends your thesis story. It's the one thing recruiters from
these postings most need to see.

**What it is:** An agentic document-intelligence API. A user asks a complex
question; a LangGraph supervisor routes between (a) a graph-retrieval agent
over Neo4j, (b) a vector-retrieval agent over a vector DB, and (c) a synthesis
agent — then returns an answer WITH its reasoning trace and a faithfulness
score. Reuse your thesis/AgriSage core; the new part is everything around it.

**The new skills it forces you to learn (the whole point):**

*Weeks 1–2 — Agentic core*
- Rebuild the agent layer in **LangGraph** (not just ReAct) — explicit state
  graph, supervisor + worker agents, conditional routing, retry/repair edges.
- Add a tool-calling agent that decides retrieval strategy per query.
- Deliverable: working multi-agent graph, runnable locally.

*Weeks 3–4 — Production on AWS*
- Containerize with Docker; write a clean FastAPI service around the graph.
- Deploy to AWS: start with **ECS Fargate** (simpler than EKS) behind an
  Application Load Balancer. Use **ECR** for images.
- Add **API Gateway + Lambda** for a lightweight auth/entry layer.
- Store secrets in AWS Secrets Manager; vector store on managed service or
  self-hosted Qdrant on the same cluster.
- Deliverable: a live public endpoint (rate-limited) + architecture diagram.

*Week 5 — MLOps & observability (the "debito, non un asset" requirement)*
- Wire **Langfuse** for full request tracing (you already know this — now in prod).
- Add **RAGAS** evaluation running on a fixed eval set in CI, so every commit
  reports faithfulness/answer-relevance deltas.
- Log latency, token cost per request, retrieval-hit-rate to CloudWatch.
- Version prompts + eval sets with **DVC**; track experiment runs with **MLflow**.
- Deliverable: a dashboard screenshot + a CI run that fails if faithfulness drops.

*Week 6 — Responsible AI + polish*
- Add a **PII-redaction** pre-processing step (recurs in postings: GDPR, OWASP).
- Write the README as a case study: problem → architecture → eval results →
  cost/latency numbers → what you'd do next.
- Record a 3-minute Loom demo.

**Why this wins:** it's the exact shape of what spektr, Explore Group, BMW, and
Humans.tech describe — "own end-to-end," "production-ready GenAI," "agentic,"
"evaluation obsession," "AWS + containers."

---

## SUPPORTING PROJECT — Fine-tuning (weeks 7–8)

Smaller, focused, closes the fine-tuning gap that ~6 postings name explicitly
(LLaMA/Mistral).

- Fine-tune a small open model (**Mistral 7B** or **Llama 3.1 8B**) with **LoRA/QLoRA**
  on a domain task — e.g. turning your CropCommand text-to-plan into a fine-tuned
  model rather than a prompted one. Direct, honest before/after comparison.
- Use Hugging Face `peft` + `trl`; train on a rented GPU (Colab Pro, Lambda, or
  a spot EC2 g5 instance — also reinforces AWS).
- Deliverable: model card on Hugging Face Hub + eval showing the fine-tune beats
  the base/prompted version on your task, with the honest caveats.

---

## TYPESCRIPT PORT — (weeks 9–10, or parallel/light)

Closes the TS gap (core at spektr + Humans.tech). Doesn't need to be big.

- Port the ProvenanceAgent **client + a thin orchestration slice** to
  **TypeScript with LangChain.js**. You don't rebuild everything — you prove you
  can work in a TS/Node LLM stack.
- Deliverable: a small Next.js or Node service calling your agent, typed
  end-to-end. Even a chat UI over your flagship API counts.

---

## What you already have (leave as-is, just document well)

- **Thesis (Graph-Native RAG)** — your anchor; make sure the repo has a clean
  README + architecture diagram + a public demo link.
- **AgriSage** — the seed of the flagship; link them in the narrative.
- **RetailIQ** — proves end-to-end ML. Good as-is.
- **FarmSmart** — proves streaming (Kafka/Spark). Good as-is.
- **Almax Mori challenge** — proves applied ML on messy real data.

---

## GitHub presentation (do this alongside, ~2 hrs/week)

Recruiters skim. Each flagship-tier repo needs:
1. One-paragraph "what + why" at the top
2. Architecture diagram (draw.io / Excalidraw)
3. "Results" section with real numbers (latency, cost, eval scores)
4. Setup that actually runs (`docker compose up`)
5. A short demo GIF or Loom link

Pin: ProvenanceAgent, thesis, RetailIQ. These three tell the whole story.

---

## 10-week schedule (~25 hrs/week)

| Wk | Focus | Learning outcome proven |
|----|-------|-------------------------|
| 1  | LangGraph multi-agent core | Agentic orchestration |
| 2  | Agent routing + tools + retry | Autonomous agents |
| 3  | Docker + FastAPI + ECS Fargate | AWS deployment |
| 4  | ALB, API Gateway, secrets, vector store | Production infra |
| 5  | Langfuse + RAGAS-in-CI + MLflow + DVC | MLOps / observability |
| 6  | PII redaction + README case study + demo | Responsible AI + polish |
| 7  | LoRA/QLoRA fine-tune setup + training | Fine-tuning |
| 8  | Fine-tune eval + HF model card | Model evaluation |
| 9  | TypeScript + LangChain.js port | TS/Node LLM stack |
| 10 | Chat UI + GitHub polish + Loom demos | Product-builder signal |

Thesis takes priority throughout — if a week slips, the fine-tune and TS port
are the compressible parts, not the flagship.

---

## What to learn, minimal resource list (don't over-collect)

- **LangGraph:** official LangGraph docs + their multi-agent tutorial. That's enough.
- **AWS (ECS/Fargate):** AWS "Deploy a container" workshop; skip the full SAA cert
  for now — you need deployment fluency, not a certificate.
- **MLOps:** MLflow + DVC quickstarts; you already know Langfuse/RAGAS.
- **Fine-tuning:** Hugging Face `peft` + `trl` LoRA guides.
- **TypeScript:** LangChain.js docs + the official TS handbook for syntax.

Build first, read only what unblocks the current step. Shipping the flagship
teaches more than any course.

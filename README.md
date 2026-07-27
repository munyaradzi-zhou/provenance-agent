# ProvenanceAgent

A **production-deployed, multi-agent RAG service** that answers multi-hop
questions over a knowledge graph + vector store, returns its reasoning trace,
and scores its own answer faithfulness.

> Built to demonstrate the full production loop that AI Engineer roles ask for:
> agentic orchestration (LangGraph), deployment (AWS ECS/Fargate), observability
> (Langfuse), evaluation-in-CI (RAGAS), and responsible-AI handling (PII redaction).

---

## The problem

Flat vector RAG breaks on **compositional questions** — where the answer requires
linking several facts that never co-occur in one chunk. ProvenanceAgent routes
each query through a supervisor agent that decides between graph traversal
(Neo4j/Cypher) and semantic retrieval, then synthesises an answer with a
faithfulness score and a visible reasoning trace.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the diagram and data flow.

```
Client → API Gateway → FastAPI (ECS Fargate)
                          │
                     LangGraph supervisor
                    ┌─────┼─────┐
              graph agent  vector agent
              (Neo4j)      (Qdrant)
                    └─────┬─────┘
                    synthesis agent
                          │
              Langfuse trace + RAGAS score → response
```

## Results

_(fill these in as you build — this section is what recruiters read)_

| Metric                                  | Value  |
| --------------------------------------- | ------ |
| Faithfulness (RAGAS)                    | TBD    |
| Answer relevance (RAGAS)                | TBD    |
| p95 latency                             | TBD ms |
| Avg cost / query                        | TBD    |
| Multi-hop accuracy vs flat RAG baseline | TBD    |

## Quickstart

```bash
# 1. clone + env
cp .env.example .env      # add your OPENAI_API_KEY, NEO4J_*, etc.

# 2. run everything locally
docker compose up          # brings up API + Neo4j + Qdrant

# 3. ask a question
curl -X POST localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What datasets fed the model that produced result X?"}'
```

## Tech stack

- **Orchestration:** LangGraph (supervisor + worker agents)
- **Retrieval:** Neo4j (graph), Qdrant (vector)
- **API:** FastAPI
- **Eval:** RAGAS (run in CI), Langfuse (tracing)
- **MLOps:** MLflow (runs), DVC (prompts + eval sets)
- **Deploy:** Docker → AWS ECR → ECS Fargate + ALB
- **Responsible AI:** PII redaction pre-processing

## License

MIT

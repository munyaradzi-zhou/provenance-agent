"""RAGAS evaluation — the CI quality gate ("evaluation obsession").

For each eval question we run BOTH:
  - the full agent (routing + graph/vector + synthesis + grader/repair), and
  - a flat-vector baseline (top-k vector retrieval -> answer; no graph, no routing)

then score both with RAGAS (faithfulness + answer relevancy) and compare. The
build FAILS if the agent's faithfulness drops below a threshold — so every commit
is measured, and regressions can't merge.

    python -m app.eval.run_eval [--limit N] [--threshold 0.6] [--baseline]

Needs OPENAI_API_KEY + Neo4j + Qdrant reachable.
"""

from __future__ import annotations

# NB: `app.eval` package __init__ installs the ragas compat shim before this runs.
import argparse
import json
import pathlib
import sys
from collections.abc import Callable

from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, ResponseRelevancy

from app.agents.graph import compiled_graph
from app.agents.prompts import load_prompt
from app.core.llm import get_llm
from app.retrieval.embeddings import get_embedder
from app.retrieval.vector import VectorRetriever

EVAL_SET = pathlib.Path("app/eval/eval_set.jsonl")
REPORT = pathlib.Path("app/eval/report.json")
FAITHFULNESS_THRESHOLD = 0.60

_vector = VectorRetriever()


def load_eval_set(limit: int | None) -> list[dict]:
    rows = [json.loads(x) for x in EVAL_SET.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows


def _contexts_from_state(state: dict) -> list[str]:
    """Reconstruct RAGAS `retrieved_contexts` from the agent's state."""
    parts: list[str] = []
    gc = (state.get("graph_context") or "").strip()
    if gc:
        parts.append(gc)
    vc = state.get("vector_context") or ""
    parts += [p.strip() for p in vc.split("\n\n") if p.strip()]
    return parts or ["(no context retrieved)"]


def run_agent(question: str) -> tuple[str, list[str]]:
    state = compiled_graph.invoke({"question": question})
    return state.get("answer", ""), _contexts_from_state(state)


def run_baseline(question: str) -> tuple[str, list[str]]:
    """Flat vector RAG: top-k passages -> single synthesis, no routing/graph/grader."""
    hits = _vector.search(question)
    contexts = [f"[{h['title']}] {h['text']}" for h in hits] or ["(no context retrieved)"]
    prompt = (
        load_prompt("synthesis")
        .replace("{question}", question)
        .replace("{graph_context}", "(none)")
        .replace("{vector_context}", "\n\n".join(contexts))
    )
    answer = str(get_llm().invoke(prompt).content).strip()
    return answer, contexts


def _score(rows: list[dict], runner: Callable[[str], tuple[str, list[str]]]) -> dict[str, float]:
    """Run `runner` over the eval rows, score with RAGAS, return metric means."""
    samples = []
    for r in rows:
        answer, contexts = runner(r["question"])
        samples.append(
            {
                "user_input": r["question"],
                "response": answer or "(no answer)",
                "retrieved_contexts": contexts,
                "reference": r["answer"],
            }
        )

    llm = LangchainLLMWrapper(get_llm())
    emb = LangchainEmbeddingsWrapper(get_embedder())
    result = evaluate(
        dataset=EvaluationDataset.from_list(samples),
        metrics=[Faithfulness(), ResponseRelevancy()],
        llm=llm,
        embeddings=emb,
        show_progress=False,
    )
    df = result.to_pandas()  # type: ignore[union-attr]
    metric_cols = [c for c in df.columns if df[c].dtype.kind == "f"]
    return {c: round(float(df[c].mean()), 3) for c in metric_cols}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="evaluate only the first N")
    ap.add_argument("--threshold", type=float, default=FAITHFULNESS_THRESHOLD)
    ap.add_argument("--baseline", action="store_true", help="also score the flat-vector baseline")
    args = ap.parse_args()

    rows = load_eval_set(args.limit)
    print(f"Evaluating {len(rows)} examples (agent{' + baseline' if args.baseline else ''})...")

    agent_means = _score(rows, run_agent)
    report: dict = {"n": len(rows), "agent": agent_means}
    print("\n=== AGENT ===")
    for k, v in agent_means.items():
        print(f"  {k:24s} {v}")

    if args.baseline:
        base_means = _score(rows, run_baseline)
        report["baseline"] = base_means
        print("\n=== FLAT-VECTOR BASELINE ===")
        for k, v in base_means.items():
            print(f"  {k:24s} {v}")

    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {REPORT}")

    faith = next((v for k, v in agent_means.items() if "faith" in k.lower()), None)
    if faith is not None and faith < args.threshold:
        print(f"\nFAIL: agent faithfulness {faith} < threshold {args.threshold}")
        sys.exit(1)
    print(f"\nPASS: agent faithfulness {faith} >= threshold {args.threshold}")


if __name__ == "__main__":
    main()

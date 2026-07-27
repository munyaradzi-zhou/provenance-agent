"""Turn the raw 12,576-example dev.json into a small, self-consistent demo corpus.

2WikiMultihopQA gives each example its OWN 10 context paragraphs + evidence
triples, so a subset is still fully answerable from what it ingests. We take a
balanced sample across the four question `type`s and emit three artifacts:

  data/processed/passages.jsonl  -> Qdrant  (unique Wikipedia paragraphs)
  data/processed/triples.jsonl   -> Neo4j   (unique subject-relation-object)
  data/processed/eval.jsonl      -> RAGAS   (question, answer, gold titles)

Deterministic: fixed seed + sorted selection, so the corpus is reproducible
(and DVC-trackable in Phase 5).

Usage:
    python -m app.ingest.subset --per-type 125
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
from collections import defaultdict
from typing import Any

RAW = pathlib.Path("data/raw/dev.json")
OUT_DIR = pathlib.Path("data/processed")
TYPES = ("compositional", "comparison", "bridge_comparison", "inference")
SEED = 42


def _passage_id(title: str) -> str:
    """Stable id from the title so the same article dedupes across examples."""
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]


def select_examples(data: list[dict[str, Any]], per_type: int) -> list[dict[str, Any]]:
    """Balanced, deterministic sample: `per_type` examples of each question type."""
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ex in data:
        by_type[ex["type"]].append(ex)

    rng = random.Random(SEED)
    chosen: list[dict[str, Any]] = []
    for t in TYPES:
        pool = sorted(by_type.get(t, []), key=lambda e: e["_id"])  # deterministic order
        rng.shuffle(pool)
        chosen.extend(pool[:per_type])
    return chosen


def build_artifacts(
    examples: list[dict[str, Any]],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Flatten selected examples into deduped passages, triples, and eval rows."""
    passages: dict[str, dict] = {}
    triples: dict[tuple[str, str, str], dict] = {}
    eval_rows: list[dict] = []

    for ex in examples:
        # passages: context is [[title, [sentence, ...]], ...]
        for title, sentences in ex["context"]:
            pid = _passage_id(title)
            if pid not in passages:
                passages[pid] = {
                    "id": pid,
                    "title": title,
                    "text": " ".join(sentences).strip(),
                }

        # triples: evidences is [[subject, relation, object], ...]
        for subj, rel, obj in ex.get("evidences", []):
            key = (subj, rel, obj)
            if key not in triples:
                triples[key] = {"subject": subj, "relation": rel, "object": obj}

        # eval row: keep gold supporting titles for retrieval hit-rate later
        gold_titles = sorted({title for title, _ in ex.get("supporting_facts", [])})
        eval_rows.append(
            {
                "id": ex["_id"],
                "question": ex["question"],
                "answer": ex["answer"],
                "type": ex["type"],
                "supporting_titles": gold_titles,
                "evidence_triples": ex.get("evidences", []),
            }
        )

    return list(passages.values()), list(triples.values()), eval_rows


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-type", type=int, default=125, help="examples per question type")
    args = ap.parse_args()

    if not RAW.exists():
        raise SystemExit(f"{RAW} not found. Download the corpus first (see data/raw/README.md).")

    data = json.loads(RAW.read_text(encoding="utf-8"))
    examples = select_examples(data, args.per_type)
    passages, triples, eval_rows = build_artifacts(examples)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_jsonl(OUT_DIR / "passages.jsonl", passages)
    _write_jsonl(OUT_DIR / "triples.jsonl", triples)
    _write_jsonl(OUT_DIR / "eval.jsonl", eval_rows)

    print(f"Selected {len(examples)} examples ({args.per_type}/type)")
    print(f"  passages.jsonl : {len(passages)} unique passages")
    print(f"  triples.jsonl  : {len(triples)} unique triples")
    print(f"  eval.jsonl     : {len(eval_rows)} questions")


if __name__ == "__main__":
    main()

"""RAGAS evaluation harness. Week 5: run this in CI, fail build if score drops.

Usage: python -m app.eval.run_eval
"""
import json
import pathlib

EVAL_SET = pathlib.Path(__file__).parent / "eval_set.jsonl"


def load_eval_set() -> list[dict]:
    if not EVAL_SET.exists():
        return []
    return [json.loads(line) for line in EVAL_SET.read_text().splitlines() if line.strip()]


def main() -> None:
    data = load_eval_set()
    print(f"Loaded {len(data)} eval examples.")
    # TODO(week5): from ragas import evaluate; compute faithfulness + answer_relevance
    # TODO(week5): assert faithfulness >= THRESHOLD else sys.exit(1)
    print("TODO: wire RAGAS here.")


if __name__ == "__main__":
    main()

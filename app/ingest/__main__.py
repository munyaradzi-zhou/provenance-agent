"""Run the full ingestion: subset (if needed) -> Neo4j -> Qdrant.

    python -m app.ingest              # graph + vectors
    python -m app.ingest --graph      # graph only
    python -m app.ingest --vectors    # vectors only

Requires the docker-compose services (Neo4j + Qdrant) to be up and, for
vectors, OPENAI_API_KEY set.
"""

from __future__ import annotations

import argparse
import pathlib

from app.ingest import build_graph, build_vectors, subset


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", action="store_true", help="graph only")
    ap.add_argument("--vectors", action="store_true", help="vectors only")
    ap.add_argument("--per-type", type=int, default=125, help="subset size per question type")
    args = ap.parse_args()

    do_graph = args.graph or not args.vectors
    do_vectors = args.vectors or not args.graph

    if not pathlib.Path("data/processed/triples.jsonl").exists():
        print("No processed corpus found — subsetting first.")
        import sys

        sys.argv = ["subset", "--per-type", str(args.per_type)]
        subset.main()

    if do_graph:
        build_graph.build()
    if do_vectors:
        build_vectors.build()


if __name__ == "__main__":
    main()

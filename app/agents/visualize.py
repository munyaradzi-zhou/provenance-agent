"""Dump the compiled LangGraph as a Mermaid diagram.

    python -m app.agents.visualize            # print mermaid to stdout
    python -m app.agents.visualize --write     # also write docs/agent_graph.md

Keeps the architecture diagram in the README honest — it's generated from the
actual compiled graph, not hand-drawn and left to rot.
"""

import argparse
import pathlib

from app.agents.graph import compiled_graph

OUT = pathlib.Path("docs/agent_graph.md")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="write docs/agent_graph.md")
    args = ap.parse_args()

    mermaid = compiled_graph.get_graph().draw_mermaid()
    print(mermaid)

    if args.write:
        OUT.write_text(f"# Agent graph (generated)\n\n```mermaid\n{mermaid}```\n", encoding="utf-8")
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

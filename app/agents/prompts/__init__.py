"""Versioned prompt templates loaded from .txt files (DVC-tracked in Phase 5).

Keeping prompts as files (not inline strings) means they can be versioned,
diffed, and evaluated independently of the code — the unit of change for prompt
engineering is the prompt, so it gets its own file.
"""

import pathlib

_DIR = pathlib.Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by stem, e.g. load_prompt('router')."""
    return (_DIR / f"{name}.txt").read_text(encoding="utf-8")

"""Eval package.

IMPORTANT: this runs before any submodule import, so it's where we install the
ragas compatibility shim. ragas 0.4.x hard-imports
`langchain_community.chat_models.vertexai.ChatVertexAI` (removed in the langchain
1.x stack the app runs on). We never use VertexAI, so inject a stub module here —
before `run_eval` imports ragas — keeping eval in the same env as the app without
downgrading langchain.
"""

import sys
import types

_MOD = "langchain_community.chat_models.vertexai"
if _MOD not in sys.modules:
    _stub = types.ModuleType(_MOD)
    _stub.ChatVertexAI = type("ChatVertexAI", (), {})  # type: ignore[attr-defined]
    sys.modules[_MOD] = _stub

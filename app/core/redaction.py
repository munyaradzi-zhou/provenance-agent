"""PII redaction pre-processing (responsible-AI requirement in postings).

Week 6: swap the regex stub for Microsoft Presidio for real coverage.
"""
import re

_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
}


def redact(text: str) -> str:
    out = text
    for label, pat in _PATTERNS.items():
        out = pat.sub(f"[{label}]", out)
    return out

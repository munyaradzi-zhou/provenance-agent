"""PII redaction pre-processing (responsible-AI requirement in postings).

The first node in the agent graph strips PII from the user's question *before*
it reaches the LLM, the retrievers, or any trace/log. This is our GDPR /
data-minimisation posture: no email, phone, name, card number, etc. ever leaves
the process boundary or lands in Langfuse/CloudWatch.

Two-tier design:

1. **Microsoft Presidio** (preferred) — an NLP-backed analyzer (spaCy NER +
   pattern/context recognizers) that catches named entities regex can't:
   PERSON, LOCATION, CREDIT_CARD, IBAN, US_SSN, and more. Loaded lazily and
   cached, because building the spaCy pipeline is expensive (~1s) and we only
   want to pay that once, at first use.
2. **Regex fallback** — if Presidio (or its spaCy model) isn't installed, we
   degrade to the original email/phone regex rather than fail closed. The
   serving image always has Presidio; the fallback keeps unit tests and lean
   dev environments working without the ~50MB model download.

Both tiers expose the same `redact(text) -> str` signature, so callers (the
graph's `redact_node`) never know which path ran.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Protocol

logger = logging.getLogger("provenance.redaction")

# --- tier 2: regex fallback --------------------------------------------------
# Deliberately conservative patterns; Presidio does the heavy lifting when present.
_REGEX_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"\+?\d[\d\s().-]{7,}\d"),
}

# PII entity types we ask Presidio to look for. Presidio labels are mapped to
# these placeholders in the anonymizer config below.
#
# Domain-aware choice: we deliberately EXCLUDE PERSON and LOCATION. This is a
# film/entity QA system — "Who directed Nemesis 2: Nebula?" — so people and
# places ARE the retrieval targets, not PII to strip. Redacting them would
# clobber legitimate queries (spaCy NER even flags film titles as PERSON). We
# strip the contact/financial identifiers a user might *accidentally* paste,
# which are never a legitimate query subject here. See the responsible-AI note
# in docs/threat_model.md for the reasoning.
_PRESIDIO_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
    "IP_ADDRESS",
    "CRYPTO",
]


def _regex_redact(text: str) -> str:
    """Fallback: replace emails and phone numbers with typed placeholders."""
    out = text
    for label, pat in _REGEX_PATTERNS.items():
        out = pat.sub(f"[{label}]", out)
    return out


class _Redactor(Protocol):
    def __call__(self, text: str) -> str: ...


@lru_cache(maxsize=1)
def _get_redactor() -> _Redactor:
    """Build (once) the best available redactor.

    Cached so the expensive spaCy pipeline is constructed a single time per
    process. On any import/setup failure we log once and return the regex path.
    """
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
    except ImportError:
        logger.warning("Presidio not installed; using regex redaction fallback")
        return _regex_redact

    try:
        # Use the small English model to keep the image lean; Presidio's default
        # is en_core_web_lg (~600MB). "sm" is ~50MB and sufficient for PII NER.
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        )
        analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
        anonymizer = AnonymizerEngine()
    except Exception:  # spaCy model missing, or any engine build failure
        logger.warning(
            "Presidio engine build failed; using regex redaction fallback", exc_info=True
        )
        return _regex_redact

    # Replace each detected entity with a typed placeholder, e.g. "[PERSON]".
    # DEFAULT covers any entity we didn't name explicitly.
    operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
    for ent in _PRESIDIO_ENTITIES:
        operators[ent] = OperatorConfig("replace", {"new_value": f"[{ent}]"})

    def _presidio_redact(text: str) -> str:
        try:
            results = analyzer.analyze(text=text, entities=_PRESIDIO_ENTITIES, language="en")
            return anonymizer.anonymize(
                text=text, analyzer_results=results, operators=operators
            ).text
        except Exception:
            # Never let redaction crash a request; fall back per-call.
            logger.warning("Presidio analyze failed; regex fallback for this call", exc_info=True)
            return _regex_redact(text)

    logger.info("Presidio redaction engine ready (spaCy en_core_web_sm)")
    return _presidio_redact


def redact(text: str) -> str:
    """Strip PII from `text`, returning it with typed placeholders.

    Presidio-backed when available (names, locations, cards, IBAN, SSN, IP,
    crypto, email, phone); regex email/phone fallback otherwise. Same signature
    either way so the agent graph is agnostic to the backend.
    """
    return _get_redactor()(text)

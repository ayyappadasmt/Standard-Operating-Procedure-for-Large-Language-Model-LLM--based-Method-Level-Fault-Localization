"""
Result Parser
=============
Extracts structured data from raw LLM text responses.
Mirrors the "Result Parser" component in Fig. 2.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from src.components.state_storage import MethodInfo, ClassInfo

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Suspicious-class extraction  (Task ❸ output)
# ─────────────────────────────────────────────────────────────────────────────

def parse_suspicious_class(
    llm_response: str,
    covered_classes: list[ClassInfo],
) -> tuple[Optional[ClassInfo], str]:
    """
    The LLM is instructed to name one class from the covered list.
    We scan the response for the first class name that appears in our list.

    Returns (ClassInfo | None, reason_text).
    """
    # build lookup {simple_name: ClassInfo, full_name: ClassInfo}
    lookup: dict[str, ClassInfo] = {}
    for ci in covered_classes:
        lookup[ci.full_name] = ci
        lookup[ci.full_name.split(".")[-1]] = ci

    for name, ci in lookup.items():
        if name in llm_response:
            reason = _extract_reason(llm_response)
            logger.info("Suspicious class identified: %s", ci.full_name)
            return ci, reason

    # fallback: return first covered class
    if covered_classes:
        logger.warning("Could not parse suspicious class — defaulting to first covered class")
        return covered_classes[0], llm_response
    return None, llm_response


# ─────────────────────────────────────────────────────────────────────────────
# Related-methods extraction  (Task ❺ output)
# ─────────────────────────────────────────────────────────────────────────────

def parse_related_methods(
    llm_response: str,
    candidate_methods: list[MethodInfo],
) -> list[MethodInfo]:
    """
    The LLM lists method names it considers related.
    We match those names against our candidate pool.
    """
    lookup: dict[str, MethodInfo] = {}
    for mi in candidate_methods:
        lookup[mi.full_name] = mi
        lookup[mi.method_name] = mi
        lookup[mi.signature]   = mi

    related: list[MethodInfo] = []
    seen: set[str] = set()

    for name, mi in lookup.items():
        if name in llm_response and mi.full_name not in seen:
            related.append(mi)
            seen.add(mi.full_name)

    if not related:
        logger.warning("No related methods parsed — using all candidates")
        related = candidate_methods

    logger.info("Related methods found: %d", len(related))
    return related


# ─────────────────────────────────────────────────────────────────────────────
# Suspiciousness score extraction  (Task ❻ output)
# ─────────────────────────────────────────────────────────────────────────────

_SCORE_RE = re.compile(r"#SCORE#\s*(\d{1,2})", re.IGNORECASE)
_ALT_SCORE_RE = re.compile(r"\bscore[:\s]+(\d{1,2})\b", re.IGNORECASE)


def parse_method_score(llm_response: str) -> tuple[int, str]:
    """
    Extract the integer score (1-10) and description from the Method Review
    response, which should follow the format: "#SCORE# <int> <description>".
    """
    m = _SCORE_RE.search(llm_response)
    if not m:
        m = _ALT_SCORE_RE.search(llm_response)

    score = int(m.group(1)) if m else 5  # default mid-range

    # everything after the score marker is the description
    if m:
        description = llm_response[m.end():].strip().lstrip("-:").strip()
    else:
        description = llm_response.strip()

    return score, description


# ─────────────────────────────────────────────────────────────────────────────
# Enhanced-doc table extraction  (Task ❹ output)
# ─────────────────────────────────────────────────────────────────────────────

_TABLE_ROW_RE = re.compile(
    r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.MULTILINE
)


def parse_enhanced_docs(
    llm_response: str,
    methods: list[MethodInfo],
) -> list[MethodInfo]:
    """
    Parse the markdown table produced by the Method Doc Enhancement task
    and update the enhanced_doc field of each matching MethodInfo.
    """
    lookup = {mi.full_name: mi for mi in methods}
    lookup.update({mi.method_name: mi for mi in methods})

    rows = _TABLE_ROW_RE.findall(llm_response)
    updated = 0
    for name_cell, doc_cell in rows:
        name_cell = name_cell.strip()
        if name_cell.lower() in ("method full name", "---", ""):
            continue
        for key, mi in lookup.items():
            if key in name_cell or name_cell in key:
                mi.enhanced_doc = doc_cell.strip()
                updated += 1
                break

    logger.info("Enhanced docs parsed for %d methods", updated)
    return methods


# ─────────────────────────────────────────────────────────────────────────────
# Generic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_reason(text: str, max_chars: int = 500) -> str:
    """Best-effort extraction of the reason/explanation portion of a response."""
    for keyword in ("because", "reason", "due to", "since", "therefore"):
        idx = text.lower().find(keyword)
        if idx != -1:
            return text[idx: idx + max_chars].strip()
    return text[:max_chars].strip()

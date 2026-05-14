"""
SOAPFL Pipeline Orchestrator
=============================
Runs the three-stage Standard Operating Procedure:

  Stage 1 — Fault Comprehension   (Tasks ❶ ❷)
  Stage 2 — Codebase Navigation   (Tasks ❸ ❹ ❺)
  Stage 3 — Fault Confirmation    (Tasks ❻ ❼)

Usage
-----
    from src.components.pipeline import SoapFLPipeline
    pipeline = SoapFLPipeline()
    results  = pipeline.run(state)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from src.components.llm_client      import LLMClient
from src.components.state_storage   import PipelineState, MethodInfo
from src.components.program_analysis import run_program_analysis
from src.components.result_parser   import (
    parse_suspicious_class,
    parse_related_methods,
    parse_method_score,
    parse_enhanced_docs,
)
from src.prompts.prompt_generator   import (
    task1_test_behavior_analysis,
    task2_test_failure_analysis,
    task3_search_suspicious_class,
    task4_method_doc_enhancement,
    task5_find_related_methods,
    task6_method_review,
    task7_rank_methods,
)
from config.settings import TOP_N_RESULTS

logger = logging.getLogger(__name__)


class SoapFLPipeline:
    """Full SOAPFL pipeline."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
        self._start_time: float = 0.0

    # ── public entry point ────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> list[MethodInfo]:
        """
        Execute all three stages and return the ranked list of suspicious methods.
        """
        self._start_time = time.time()
        logger.info("=" * 60)
        logger.info("SOAPFL starting for bug: %s / %s", state.project_name, state.bug_id)
        logger.info("=" * 60)

        # ── Pre-processing: Program Analysis ─────────────────────────────────
        run_program_analysis(state)

        # ── Stage 1 ───────────────────────────────────────────────────────────
        self._stage1_fault_comprehension(state)

        # ── Stage 2 ───────────────────────────────────────────────────────────
        self._stage2_codebase_navigation(state)

        # ── Stage 3 ───────────────────────────────────────────────────────────
        self._stage3_fault_confirmation(state)

        elapsed = time.time() - self._start_time
        token_info = self.llm.token_summary()
        logger.info("-" * 60)
        logger.info("Done in %.1f s | tokens: %s", elapsed, token_info)
        logger.info("-" * 60)

        return state.final_ranking[:TOP_N_RESULTS]

    # ── Stage 1 ───────────────────────────────────────────────────────────────

    def _stage1_fault_comprehension(self, state: PipelineState) -> None:
        logger.info("[Stage 1] Fault Comprehension")

        # Task ❶ — Test Behavior Analysis
        logger.info("  Task ❶ Test Behavior Analysis …")
        sys_p, user_msg = task1_test_behavior_analysis(state)
        state.test_behavior = self.llm.chat(sys_p, user_msg)
        logger.debug("  test_behavior snippet: %s…", state.test_behavior[:120])

        # Task ❷ — Test Failure Analysis
        logger.info("  Task ❷ Test Failure Analysis …")
        sys_p, user_msg = task2_test_failure_analysis(state)
        state.possible_causes = self.llm.chat(sys_p, user_msg)
        logger.debug("  possible_causes snippet: %s…", state.possible_causes[:120])

    # ── Stage 2 ───────────────────────────────────────────────────────────────

    def _stage2_codebase_navigation(self, state: PipelineState) -> None:
        logger.info("[Stage 2] Codebase Navigation")

        if not state.covered_classes:
            logger.warning("  No covered classes found — skipping navigation stage")
            return

        # Task ❸ — Search Suspicious Class
        logger.info("  Task ❸ Search Suspicious Class …")
        sys_p, user_msg = task3_search_suspicious_class(state)
        response3 = self.llm.chat(sys_p, user_msg)
        state.suspicious_class, state.suspicious_class_reason = parse_suspicious_class(
            response3, state.covered_classes
        )

        if not state.suspicious_class:
            logger.warning("  Could not identify suspicious class")
            return

        logger.info("  → Suspicious class: %s", state.suspicious_class.full_name)

        # Task ❹ — Method Doc Enhancement
        logger.info("  Task ❹ Method Doc Enhancement …")
        sys_p, user_msg = task4_method_doc_enhancement(state)
        response4 = self.llm.chat(sys_p, user_msg)
        state.suspicious_class.covered_methods = parse_enhanced_docs(
            response4, state.suspicious_class.covered_methods
        )
        state.enhanced_methods = state.suspicious_class.covered_methods

        # Task ❺ — Find Related Methods
        logger.info("  Task ❺ Find Related Methods …")
        sys_p, user_msg = task5_find_related_methods(state)
        response5 = self.llm.chat(sys_p, user_msg)
        state.related_methods = parse_related_methods(
            response5, state.suspicious_class.covered_methods
        )
        logger.info("  → %d related methods identified", len(state.related_methods))

    # ── Stage 3 ───────────────────────────────────────────────────────────────

    def _stage3_fault_confirmation(self, state: PipelineState) -> None:
        logger.info("[Stage 3] Fault Confirmation")

        candidates = state.related_methods or state.enhanced_methods
        if not candidates:
            logger.warning("  No candidate methods for confirmation")
            return

        # Task ❻ — Method Review (multi-round dialogue, one method at a time)
        reviewed: list[MethodInfo] = []
        for idx, method in enumerate(candidates, 1):
            logger.info(
                "  Task ❻ Reviewing method %d/%d: %s …",
                idx, len(candidates), method.method_name,
            )
            sys_p, user_msg = task6_method_review(state, method)
            response6 = self.llm.chat(sys_p, user_msg)
            score, reason = parse_method_score(response6)
            method.suspiciousness_score  = score
            method.suspiciousness_reason = reason
            reviewed.append(method)

        state.reviewed_methods = reviewed

        # Task ❼ — Suspicious Method Ranking
        logger.info("  Task ❼ Ranking suspicious methods …")
        state.final_ranking = task7_rank_methods(reviewed)

        # log top results
        for rank, mi in enumerate(state.final_ranking[:TOP_N_RESULTS], 1):
            logger.info(
                "  #%d [score=%d] %s", rank, mi.suspiciousness_score, mi.full_name
            )

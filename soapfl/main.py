#!/usr/bin/env python3
"""
SOAPFL — Standard Operating Procedure for LLM-Based Fault Localization
=======================================================================

Usage
-----
Run on the built-in sample bug:
    python main.py

Run on a custom bug directory:
    python main.py --bug-dir tests/sample_bugs/Lang_10

Run on a specific Defects4J-style input dict (programmatic):
    See src/utils/loader.py :: load_from_dict()
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

try:
    from rich.logging import RichHandler
    _handler = RichHandler(rich_tracebacks=True, show_path=False)
    _fmt = "%(message)s"
except ImportError:
    _handler = logging.StreamHandler()
    _fmt = "%(asctime)s %(levelname)s %(message)s"

# ── configure logging ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format=_fmt, handlers=[_handler])
logger = logging.getLogger("soapfl")


def main(args: argparse.Namespace) -> None:
    from src.utils.loader       import load_from_directory
    from src.components.pipeline import SoapFLPipeline
    from src.utils.report        import print_results, save_results

    # ── load bug ──────────────────────────────────────────────────────────────
    bug_dir = args.bug_dir or "tests/sample_bugs/Lang_10"
    logger.info("Loading bug from: %s", bug_dir)
    state = load_from_directory(bug_dir)

    # ── run pipeline ──────────────────────────────────────────────────────────
    pipeline = SoapFLPipeline()
    t0 = time.time()
    ranked_methods = pipeline.run(state)
    elapsed = time.time() - t0

    # ── report ────────────────────────────────────────────────────────────────
    token_summary = pipeline.llm.token_summary()
    print_results(state, ranked_methods, elapsed, token_summary)
    save_results(state, ranked_methods, elapsed, token_summary)
    state.save()

    # ── exit code: 0 if Top-1 exists, 1 otherwise ────────────────────────────
    sys.exit(0 if ranked_methods else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SOAPFL — LLM-based method-level fault localization (Groq backend)"
    )
    parser.add_argument(
        "--bug-dir",
        type=str,
        default=None,
        help="Path to bug directory (default: tests/sample_bugs/Lang_10)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING"],
        default="INFO",
        help="Logging verbosity",
    )
    parsed = parser.parse_args()
    logging.getLogger().setLevel(parsed.log_level)
    main(parsed)

"""
Bug Loader
==========
Loads a bug specification from a directory or a Python dict and populates
a PipelineState ready for the SOAPFL pipeline.

Directory layout expected:
    <bug_dir>/
        bug.json          — metadata (project, bug_id, test_class, failed_tests)
        tests/
            <TestClass>.java    — failed test source(s)
        src/
            **/*.java           — production source files
        errors/
            <test_name>.txt     — error messages / stack traces
"""
from __future__ import annotations

import json
import os
import glob
import logging

from src.components.state_storage import PipelineState

logger = logging.getLogger(__name__)


def load_from_directory(bug_dir: str) -> PipelineState:
    """Load a bug specification from the standardised directory layout."""
    meta_path = os.path.join(bug_dir, "bug.json")
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(f"bug.json not found in {bug_dir}")

    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    state = PipelineState(
        project_name=meta.get("project", "unknown"),
        bug_id=meta.get("bug_id", "unknown"),
        test_class=meta.get("test_class", ""),
        failed_tests=meta.get("failed_tests", []),
    )

    # load test sources
    test_dir = os.path.join(bug_dir, "tests")
    if os.path.isdir(test_dir):
        for java_file in glob.glob(os.path.join(test_dir, "**", "*.java"), recursive=True):
            name = os.path.basename(java_file).replace(".java", "")
            with open(java_file, encoding="utf-8", errors="replace") as fh:
                state.test_code[name] = fh.read()

    # load production sources
    src_dir = os.path.join(bug_dir, "src")
    if os.path.isdir(src_dir):
        for java_file in glob.glob(os.path.join(src_dir, "**", "*.java"), recursive=True):
            rel = os.path.relpath(java_file, src_dir)
            with open(java_file, encoding="utf-8", errors="replace") as fh:
                state.source_files[rel] = fh.read()

    # load error messages
    err_dir = os.path.join(bug_dir, "errors")
    if os.path.isdir(err_dir):
        for txt_file in glob.glob(os.path.join(err_dir, "*.txt")):
            name = os.path.basename(txt_file).replace(".txt", "")
            with open(txt_file, encoding="utf-8", errors="replace") as fh:
                state.error_messages[name] = fh.read()[:800]

    logger.info(
        "Loaded bug %s/%s: %d test files, %d source files, %d error files",
        state.project_name, state.bug_id,
        len(state.test_code), len(state.source_files), len(state.error_messages),
    )
    return state


def load_from_dict(bug_dict: dict) -> PipelineState:
    """
    Load a bug specification from a Python dictionary.
    Useful for programmatic/testing usage.

    Expected keys
    -------------
    project      : str
    bug_id       : str
    test_class   : str
    failed_tests : list[str]
    test_code    : dict[str, str]   — {test_name: java_source}
    source_files : dict[str, str]   — {relative_path: java_source}
    error_messages: dict[str, str]  — {test_name: stack_trace}
    """
    state = PipelineState(
        project_name=bug_dict.get("project", "unknown"),
        bug_id=bug_dict.get("bug_id", "unknown"),
        test_class=bug_dict.get("test_class", ""),
        failed_tests=bug_dict.get("failed_tests", []),
    )
    state.test_code      = bug_dict.get("test_code", {})
    state.source_files   = bug_dict.get("source_files", {})
    state.error_messages = bug_dict.get("error_messages", {})
    return state

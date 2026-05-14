"""
State Storage — holds all intermediate results that flow between pipeline tasks.
Mirrors the "State Storage" box in the SOAPFL architecture diagram (Fig. 2).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from config.settings import OUTPUT_DIR


@dataclass
class MethodInfo:
    full_name: str          # e.g. "com.example.Foo::bar(int)"
    class_name: str
    method_name: str
    signature: str
    doc: str = ""
    enhanced_doc: str = ""
    code: str = ""
    suspiciousness_score: int = 0
    suspiciousness_reason: str = ""


@dataclass
class ClassInfo:
    full_name: str          # e.g. "com.example.Foo"
    doc: str = ""
    covered_methods: list[MethodInfo] = field(default_factory=list)


@dataclass
class PipelineState:
    # ── inputs ────────────────────────────────────────────────────────────────
    project_name: str = ""
    bug_id: str = ""
    test_class: str = ""
    failed_tests: list[str] = field(default_factory=list)
    test_code: dict[str, str] = field(default_factory=dict)   # name → source
    test_utility_code: dict[str, str] = field(default_factory=dict)
    error_messages: dict[str, str] = field(default_factory=dict)
    source_files: dict[str, str] = field(default_factory=dict)  # path → source

    # ── Task ❶ — Test Behavior Analysis ───────────────────────────────────────
    test_behavior: str = ""

    # ── Task ❷ — Test Failure Analysis ───────────────────────────────────────
    possible_causes: str = ""

    # ── Program Analysis — covered classes/methods ────────────────────────────
    covered_classes: list[ClassInfo] = field(default_factory=list)

    # ── Task ❸ — Search Suspicious Class ─────────────────────────────────────
    suspicious_class: Optional[ClassInfo] = None
    suspicious_class_reason: str = ""

    # ── Task ❹ — Method Doc Enhancement ─────────────────────────────────────
    enhanced_methods: list[MethodInfo] = field(default_factory=list)

    # ── Task ❺ — Find Related Methods ────────────────────────────────────────
    related_methods: list[MethodInfo] = field(default_factory=list)

    # ── Task ❻ — Method Review (multi-round) ─────────────────────────────────
    reviewed_methods: list[MethodInfo] = field(default_factory=list)

    # ── Task ❼ — Suspicious Method Ranking ───────────────────────────────────
    final_ranking: list[MethodInfo] = field(default_factory=list)

    def save(self, path: Optional[str] = None) -> str:
        if path is None:
            fname = f"{self.project_name}_{self.bug_id}_state.json"
            path = os.path.join(OUTPUT_DIR, fname)

        # Convert dataclass tree → dict
        def _convert(obj):
            if isinstance(obj, (MethodInfo, ClassInfo, PipelineState)):
                return {k: _convert(v) for k, v in asdict(obj).items()}
            if isinstance(obj, list):
                return [_convert(i) for i in obj]
            return obj

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_convert(self), fh, indent=2)
        return path

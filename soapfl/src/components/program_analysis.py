"""
Program Analysis Component
==========================
Implements the two sub-components described in the paper:

  1. Static Analysis   — parse Java source with `javalang` to extract
                          classes, methods, signatures, and Javadoc comments.

  2. Test Behavior Tracking (simulated dynamic) — in the real SOAPFL a JVM
     agent instruments bytecode at runtime; in this prototype we simulate
     that by following `import` / method-call patterns in the test source
     with a regex heuristic, then resolving them against known source files.

Both produce ClassInfo / MethodInfo objects written into PipelineState.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

try:
    import javalang
    JAVALANG_OK = True
except ImportError:
    JAVALANG_OK = False

from src.components.state_storage import ClassInfo, MethodInfo, PipelineState
from config.settings import MAX_COVERED_CLASSES, MAX_COVERED_METHODS

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

_JAVADOC_RE = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
_CLASS_RE   = re.compile(
    r"(?:public|protected|private|abstract|final|\s)*\s+class\s+(\w+)", re.MULTILINE
)
_METHOD_RE  = re.compile(
    r"(?:public|protected|private|static|final|synchronized|abstract|\s)+"
    r"(?:<[^>]+>\s+)?(\w[\w<>\[\]]*)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws[^{;]+)?[{;]",
    re.MULTILINE,
)
_IMPORT_RE  = re.compile(r"^\s*import\s+([\w.]+);", re.MULTILINE)
_CALL_RE    = re.compile(r"\b(\w+)\s*\(", re.MULTILINE)


def _extract_javadoc(source: str, start_pos: int) -> str:
    """Return the Javadoc comment immediately preceding `start_pos`."""
    snippet = source[:start_pos]
    match = None
    for match in _JAVADOC_RE.finditer(snippet):
        pass
    if match:
        text = match.group(1)
        # strip leading * from each line
        lines = [l.strip().lstrip("*").strip() for l in text.splitlines()]
        return " ".join(l for l in lines if l)
    return ""


def _truncate(text: str, max_tokens: int = 100) -> str:
    """Rough token truncation (1 token ≈ 4 chars)."""
    limit = max_tokens * 4
    return text[:limit] + "…" if len(text) > limit else text


# ─────────────────────────────────────────────────────────────────────────────
# Static Analysis
# ─────────────────────────────────────────────────────────────────────────────

def parse_java_source(class_name: str, source: str) -> ClassInfo:
    """
    Parse a Java source string and return a ClassInfo populated with
    MethodInfo objects.  Falls back to regex when `javalang` is unavailable
    or raises a parse error.
    """
    ci = ClassInfo(full_name=class_name)

    # ── try javalang first ────────────────────────────────────────────────────
    if JAVALANG_OK:
        try:
            tree = javalang.parse.parse(source)
            for _, node in tree.filter(javalang.tree.ClassDeclaration):
                # class-level Javadoc
                if node.documentation:
                    ci.doc = _truncate(node.documentation.strip("/**/ \n"))

                for method in (node.methods or []):
                    params = ", ".join(
                        f"{p.type.name} {p.name}" for p in (method.parameters or [])
                    )
                    sig = f"{method.name}({params})"
                    full = f"{class_name}::{sig}"
                    doc  = _truncate(method.documentation.strip("/**/ \n")) \
                           if method.documentation else ""

                    # reconstruct minimal code snippet
                    code = _method_code_snippet(source, method.name, params)

                    mi = MethodInfo(
                        full_name=full,
                        class_name=class_name,
                        method_name=method.name,
                        signature=sig,
                        doc=doc,
                        code=code,
                    )
                    ci.covered_methods.append(mi)
            return ci
        except Exception as exc:
            logger.debug("javalang parse error for %s: %s — falling back to regex", class_name, exc)

    # ── regex fallback ────────────────────────────────────────────────────────
    _class_match = _CLASS_RE.search(source)
    if _class_match:
        ci.doc = f"Class {_class_match.group(1)}"

    for m in _METHOD_RE.finditer(source):
        ret_type    = m.group(1)
        method_name = m.group(2)
        params_raw  = m.group(3).strip()
        if ret_type in ("class", "interface", "enum", "if", "while", "for"):
            continue
        sig  = f"{method_name}({params_raw})"
        full = f"{class_name}::{sig}"
        doc  = _extract_javadoc(source, m.start())
        code = _method_code_snippet(source, method_name, params_raw)

        mi = MethodInfo(
            full_name=full,
            class_name=class_name,
            method_name=method_name,
            signature=sig,
            doc=_truncate(doc) if doc else "",
            code=code,
        )
        ci.covered_methods.append(mi)

    return ci


def _method_code_snippet(source: str, method_name: str, params: str, max_lines: int = 30) -> str:
    """Extract up to max_lines of the method body."""
    pattern = re.compile(
        rf"\b{re.escape(method_name)}\s*\([^)]*\)\s*(?:throws[^{{]+)?{{",
        re.MULTILINE,
    )
    m = pattern.search(source)
    if not m:
        return ""
    start = m.start()
    lines = source[start:].splitlines()
    return "\n".join(lines[:max_lines])


# ─────────────────────────────────────────────────────────────────────────────
# Test Behavior Tracking (simulated)
# ─────────────────────────────────────────────────────────────────────────────

def track_test_utilities(
    test_class_source: str,
    all_sources: dict[str, str],
) -> dict[str, str]:
    """
    Simulate the JVM instrumentation step.

    In the real system a JVM agent records the actual Method Call Trace at
    runtime; here we approximate by:
      1. Collecting import statements from the test class.
      2. Finding method calls in the test body.
      3. Matching those calls against available source files.

    Returns a dict {class_name: source_snippet} of utility code discovered.
    """
    imports   = _IMPORT_RE.findall(test_class_source)
    calls     = set(_CALL_RE.findall(test_class_source))

    utilities: dict[str, str] = {}

    for imp in imports:
        simple = imp.split(".")[-1]
        # look for a matching source file
        for path, src in all_sources.items():
            if simple in path or imp.replace(".", "/") in path:
                # check if any call name appears in this file
                if any(call in src for call in calls):
                    utilities[imp] = src[:2000]  # first 2 k chars
                    break

    return utilities


# ─────────────────────────────────────────────────────────────────────────────
# Class Intersection
# ─────────────────────────────────────────────────────────────────────────────

def class_intersection(covered_per_test: list[list[str]]) -> list[str]:
    """Return classes covered by ALL failed tests (intersection)."""
    if not covered_per_test:
        return []
    common = set(covered_per_test[0])
    for lst in covered_per_test[1:]:
        common &= set(lst)
    return sorted(common)


# ─────────────────────────────────────────────────────────────────────────────
# Full Program Analysis orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_program_analysis(state: PipelineState) -> None:
    """
    Populate state.covered_classes and state.test_utility_code
    from the raw source files stored in state.source_files.

    Called before Task ❶ and Task ❸ (as described in paper §III-B, Fig. 4).
    """
    logger.info("Running program analysis …")

    # ── test utility tracking ─────────────────────────────────────────────────
    for test_name, test_src in state.test_code.items():
        utilities = track_test_utilities(test_src, state.source_files)
        state.test_utility_code.update(utilities)

    # ── static analysis of source files ───────────────────────────────────────
    classes: list[ClassInfo] = []
    for path, src in state.source_files.items():
        # derive class name from path, e.g. src/com/example/Foo.java → com.example.Foo
        class_name = _path_to_classname(path)
        ci = parse_java_source(class_name, src)
        if ci.covered_methods:
            classes.append(ci)

    # ── class intersection (all tests cover these classes) ────────────────────
    # For simplicity: every parsed production class is "covered"
    # (in real SOAPFL the JVM trace would give us the real covered set)
    state.covered_classes = classes[:MAX_COVERED_CLASSES]

    logger.info(
        "Program analysis complete: %d covered classes, %d utility sources",
        len(state.covered_classes),
        len(state.test_utility_code),
    )


def _path_to_classname(path: str) -> str:
    """Convert a file path to a Java fully-qualified class name."""
    # normalise separators
    p = path.replace("\\", "/")
    # strip leading dirs up to src/ or main/
    for marker in ("src/main/java/", "src/", "main/"):
        if marker in p:
            p = p.split(marker, 1)[1]
            break
    return p.replace("/", ".").removesuffix(".java")

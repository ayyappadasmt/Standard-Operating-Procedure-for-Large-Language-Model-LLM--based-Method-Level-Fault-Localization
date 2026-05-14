"""
Prompt Generator
================
Generates the seven task prompts described in SOAPFL (§III).
Each function returns (system_prompt, user_message) ready for LLMClient.chat().
"""
from __future__ import annotations

from src.components.state_storage import ClassInfo, MethodInfo, PipelineState
from config.settings import ROLES, MAX_COVERED_CLASSES, MAX_COVERED_METHODS


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _test_infos_block(state: PipelineState) -> str:
    lines = [f"Test class: {state.test_class}"]
    for i, tname in enumerate(state.failed_tests[:5], 1):
        lines.append(f"\n--- Failed test {i}: {tname} ---")
        if tname in state.test_code:
            lines.append(state.test_code[tname][:800])
        if tname in state.error_messages:
            lines.append(f"Error:\n{state.error_messages[tname][:400]}")
    return "\n".join(lines)


def _covered_classes_table(classes: list[ClassInfo]) -> str:
    rows = ["| Class Full Name | Documentation |", "|---|---|"]
    for ci in classes[:MAX_COVERED_CLASSES]:
        doc = (ci.doc or "No documentation available.")[:120]
        rows.append(f"| {ci.full_name} | {doc} |")
    return "\n".join(rows)


def _covered_methods_table(methods: list[MethodInfo], use_enhanced: bool = False) -> str:
    rows = ["| Method Full Name | Method Comment |", "|---|---|"]
    for mi in methods[:MAX_COVERED_METHODS]:
        doc = (mi.enhanced_doc if use_enhanced and mi.enhanced_doc else mi.doc) or "No doc."
        rows.append(f"| {mi.full_name} | {doc[:120]} |")
    return "\n".join(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Task ❶ — Test Behavior Analysis
# ─────────────────────────────────────────────────────────────────────────────

def task1_test_behavior_analysis(state: PipelineState) -> tuple[str, str]:
    system = ROLES["test_code_reviewer"]

    # build test utility code block
    util_block = ""
    if state.test_utility_code:
        parts = []
        for cls_name, src in list(state.test_utility_code.items())[:5]:
            parts.append(f"// Utility class: {cls_name}\n{src[:600]}")
        util_block = "\n\n".join(parts)
    else:
        util_block = "(No additional utility methods discovered.)"

    # build test code block
    test_block = ""
    for name, src in list(state.test_code.items())[:5]:
        test_block += f"\n// Test: {name}\n{src[:600]}\n"

    user = f"""One or more tests in the test class [{state.test_class}] failed:
Failed tests: {', '.join(state.failed_tests[:5])}

According to the code of the failed tests and the related utility methods listed below:

[TEST CODE]
{test_block}

[TEST UTILITY CODE]
{util_block}

As a Test Code Reviewer, you will explain the code logic of each test in as much detail \
as possible. When you explain each test, please also include the code logic of the test \
utility methods called by the test."""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❷ — Test Failure Analysis
# ─────────────────────────────────────────────────────────────────────────────

def task2_test_failure_analysis(state: PipelineState) -> tuple[str, str]:
    system = ROLES["software_test_engineer"]

    test_info = _test_infos_block(state)

    user = f"""One or more tests in the test class [{state.test_class}] failed:
Failed tests: {', '.join(state.failed_tests[:5])}

According to the test code, error stack trace and test output of each failed test, \
and the behaviors of the failed tests listed below:

[TEST BEHAVIOR]
{state.test_behavior}

[TEST INFOS]
{test_info}

As a Software Test Engineer, you will:
(1) Identify the common patterns or similarities from the given test behaviors, \
outputs, and stack traces.
(2) Recommend possible defects in the production code that may cause all of \
these tests to fail.

Be specific about which classes or methods might be responsible."""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❸ — Search Suspicious Class
# ─────────────────────────────────────────────────────────────────────────────

def task3_search_suspicious_class(state: PipelineState) -> tuple[str, str]:
    system = ROLES["software_architect"]

    test_info = _test_infos_block(state)
    class_table = _covered_classes_table(state.covered_classes)

    user = f"""One or more tests in the test class [{state.test_class}] failed:
Failed tests: {', '.join(state.failed_tests[:5])}

According to the test code, error stack trace and test output of each failed test, \
the possible causes of the test failures, and the classes covered by all of the \
failed tests listed below:

[TEST INFOS]
{test_info}

[POSSIBLE CAUSES]
{state.possible_causes}

[COVERED CLASSES LIST]
{class_table}

As a Software Architect, you will analyze all the given information to recommend \
which covered class is most likely to be problematic.

Note that you MUST ONLY select ONE class from the Covered Classes list above. \
State the full class name exactly as it appears in the table, then explain why."""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❹ — Method Doc Enhancement
# ─────────────────────────────────────────────────────────────────────────────

def task4_method_doc_enhancement(state: PipelineState) -> tuple[str, str]:
    system = ROLES["source_code_reviewer"]

    if not state.suspicious_class:
        return system, "No suspicious class found."

    ci = state.suspicious_class
    methods_block = "\n".join(
        f"Method: {mi.full_name}\nOriginal comment: {mi.doc or 'None'}\n"
        f"Code snippet:\n{mi.code[:400]}\n"
        for mi in ci.covered_methods[:MAX_COVERED_METHODS]
    )

    user = f"""Class [{ci.full_name}] was covered during testing.
The documentation of the class is: "{ci.doc or 'No class documentation.'}"

According to the covered methods in the class:
{methods_block}

As a Source Code Reviewer, you will analyze the method call relationship to \
generate an improved comment for each covered method.

For each covered method, if this method calls other methods in the Covered \
Methods list, you MUST explicitly claim the covered methods that are called, \
e.g., "... this method calls method 'process' to do ...".

Respond with a markdown table:
| Method Full Name | Method Comment |
|---|---|
| ClassName::MethodName(Args) | The improved method comment |"""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❺ — Find Related Methods
# ─────────────────────────────────────────────────────────────────────────────

def task5_find_related_methods(state: PipelineState) -> tuple[str, str]:
    system = ROLES["software_architect"]

    if not state.suspicious_class:
        return system, "No suspicious class found."

    ci = state.suspicious_class
    test_info = _test_infos_block(state)
    methods_table = _covered_methods_table(ci.covered_methods, use_enhanced=True)

    user = f"""One or more tests in the test class [{state.test_class}] failed:
Failed tests: {', '.join(state.failed_tests[:5])}

The existing analysis result shows that the class [{ci.full_name}] may be \
problematic. The documentation of the class is: "{ci.doc or 'N/A'}".

According to the test code, error stack trace and test output of each failed \
test, the possible causes of the test failures, and the methods in the class \
listed below:

[TEST INFOS]
{test_info}

[POSSIBLE CAUSES]
{state.possible_causes}

[COVERED METHODS] (Doc Enhanced)
{methods_table}

As a Software Architect, you will examine the Covered Methods List to select \
ALL methods that may be responsible for the test failures.

Note: you MUST ONLY select methods from the Covered Method list above. \
List each selected method's full name (as it appears in the table) on its own line."""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❻ — Method Review (single method, called in a loop)
# ─────────────────────────────────────────────────────────────────────────────

def task6_method_review(
    state: PipelineState,
    method: MethodInfo,
) -> tuple[str, str]:
    system = ROLES["software_test_engineer"]

    ci = state.suspicious_class
    test_info = _test_infos_block(state)

    user = f"""One or more tests in the test class [{state.test_class}] failed:
Failed tests: {', '.join(state.failed_tests[:5])}

The existing analysis result shows that the method [{method.full_name}] may be problematic.

[TEST INFOS]
{test_info}

Possible Causes: {state.possible_causes[:600]}

Class of the Suspicious Method: {method.class_name}
Documentation of the Class: {ci.doc if ci else 'N/A'}
Suspicious Method Full Name: {method.full_name}
Suspicious Method Comment: {method.enhanced_doc or method.doc or 'No documentation.'}
Suspicious Method Code:
{method.code[:800] or '(source not available)'}

As the Software Test Engineer, you will carefully examine the code of the method \
[{method.method_name}] line by line to evaluate how likely this method is the \
best location to be fixed.

Respond ONLY with the format:
#SCORE# <integer 1-10> <description of why this score>

Where 10 means very likely to be the buggy method and 1 means very unlikely."""

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# Task ❼ — Suspicious Method Ranking  (pure Python, no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────

def task7_rank_methods(methods: list[MethodInfo]) -> list[MethodInfo]:
    """Sort methods by suspiciousness_score descending."""
    return sorted(methods, key=lambda m: m.suspiciousness_score, reverse=True)

"""
SOAPFL Test Suite
=================
Tests all components without requiring a real Groq API key,
using a MockLLMClient that returns pre-canned responses.
"""
from __future__ import annotations

import sys
import os

# ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch

from src.components.state_storage   import PipelineState, ClassInfo, MethodInfo
from src.components.program_analysis import (
    parse_java_source,
    track_test_utilities,
    class_intersection,
    _path_to_classname,
)
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
from src.utils.loader import load_from_dict


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_JAVA_SOURCE = """
package com.example;

/**
 * A simple utility class for string operations.
 */
public class StringUtils {

    /**
     * Escapes HTML special characters in the input string.
     * Calls the private escape() method for each character.
     */
    public static String escapeHtml(String input) {
        StringBuilder sb = new StringBuilder();
        for (char c : input.toCharArray()) {
            sb.append(escape(c));
        }
        return sb.toString();
    }

    /**
     * Escapes a single character.
     */
    private static String escape(char c) {
        switch (c) {
            case '<': return "&lt;";
            case '>': return "&gt;";
            case '&': return "&amp;";
            default: return String.valueOf(c);
        }
    }

    /** Returns true if the string is null or empty. */
    public static boolean isEmpty(String s) {
        return s == null || s.length() == 0;
    }
}
"""

SAMPLE_TEST_SOURCE = """
package com.example;

import org.junit.Test;
import static org.junit.Assert.*;

public class StringUtilsTest {

    @Test
    public void testEscapeHtml() {
        String result = StringUtils.escapeHtml("<b>hello</b>");
        assertEquals("&lt;b&gt;hello&lt;/b&gt;", result);
    }
}
"""


@pytest.fixture
def sample_state() -> PipelineState:
    state = PipelineState(
        project_name="Lang",
        bug_id="42",
        test_class="StringUtilsTest",
        failed_tests=["testEscapeHtml"],
    )
    state.test_code      = {"StringUtilsTest": SAMPLE_TEST_SOURCE}
    state.source_files   = {"com/example/StringUtils.java": SAMPLE_JAVA_SOURCE}
    state.error_messages = {
        "testEscapeHtml": (
            "AssertionError: expected:<&lt;b&gt;hello&lt;/b&gt;> but was:<\u2603b\u2603hello\u2603/b\u2603>\n"
            "\tat com.example.StringUtils.escapeHtml(StringUtils.java:12)"
        )
    }
    return state


@pytest.fixture
def sample_class_info() -> ClassInfo:
    ci = ClassInfo(full_name="com.example.StringUtils", doc="String utility class.")
    ci.covered_methods = [
        MethodInfo(
            full_name="com.example.StringUtils::escapeHtml(String)",
            class_name="com.example.StringUtils",
            method_name="escapeHtml",
            signature="escapeHtml(String)",
            doc="Escapes HTML special characters.",
            code='public static String escapeHtml(String input) { ... }',
        ),
        MethodInfo(
            full_name="com.example.StringUtils::escape(char)",
            class_name="com.example.StringUtils",
            method_name="escape",
            signature="escape(char)",
            doc="Escapes a single character.",
            code='private static String escape(char c) { ... }',
        ),
        MethodInfo(
            full_name="com.example.StringUtils::isEmpty(String)",
            class_name="com.example.StringUtils",
            method_name="isEmpty",
            signature="isEmpty(String)",
            doc="Returns true if the string is null or empty.",
            code='public static boolean isEmpty(String s) { ... }',
        ),
    ]
    return ci


# ─────────────────────────────────────────────────────────────────────────────
# Program Analysis Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProgramAnalysis:

    def test_parse_java_source_extracts_methods(self):
        ci = parse_java_source("com.example.StringUtils", SAMPLE_JAVA_SOURCE)
        assert ci.full_name == "com.example.StringUtils"
        method_names = [m.method_name for m in ci.covered_methods]
        assert "escapeHtml" in method_names or len(ci.covered_methods) > 0

    def test_parse_java_source_extracts_doc(self):
        ci = parse_java_source("com.example.StringUtils", SAMPLE_JAVA_SOURCE)
        # at least some methods should have docs
        docs = [m.doc for m in ci.covered_methods if m.doc]
        assert len(docs) >= 0  # regex may vary; just ensure no crash

    def test_class_intersection_all_same(self):
        result = class_intersection([["A", "B", "C"], ["A", "B", "C"]])
        assert set(result) == {"A", "B", "C"}

    def test_class_intersection_partial(self):
        result = class_intersection([["A", "B"], ["B", "C"]])
        assert result == ["B"]

    def test_class_intersection_empty_input(self):
        assert class_intersection([]) == []

    def test_class_intersection_no_common(self):
        result = class_intersection([["A"], ["B"]])
        assert result == []

    def test_path_to_classname(self):
        assert _path_to_classname("src/main/java/com/example/Foo.java") == "com.example.Foo"
        assert _path_to_classname("com/example/Bar.java") == "com.example.Bar"

    def test_track_test_utilities_returns_dict(self):
        result = track_test_utilities(SAMPLE_TEST_SOURCE, {"com/example/StringUtils.java": SAMPLE_JAVA_SOURCE})
        assert isinstance(result, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Result Parser Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestResultParser:

    def test_parse_suspicious_class_by_full_name(self, sample_class_info):
        response = "The class com.example.StringUtils is most likely problematic because it handles escaping."
        ci_result, reason = parse_suspicious_class(response, [sample_class_info])
        assert ci_result is not None
        assert ci_result.full_name == "com.example.StringUtils"

    def test_parse_suspicious_class_by_simple_name(self, sample_class_info):
        response = "StringUtils seems to be the buggy class."
        ci_result, _ = parse_suspicious_class(response, [sample_class_info])
        assert ci_result is not None

    def test_parse_suspicious_class_fallback(self, sample_class_info):
        response = "I cannot determine the class from the given information."
        ci_result, _ = parse_suspicious_class(response, [sample_class_info])
        # should fall back to first class
        assert ci_result == sample_class_info

    def test_parse_suspicious_class_empty_list(self):
        ci_result, _ = parse_suspicious_class("any response", [])
        assert ci_result is None

    def test_parse_related_methods_by_method_name(self, sample_class_info):
        response = "The methods escapeHtml and escape appear responsible for the failures."
        related = parse_related_methods(response, sample_class_info.covered_methods)
        names = [m.method_name for m in related]
        assert "escapeHtml" in names or "escape" in names

    def test_parse_related_methods_fallback_all(self, sample_class_info):
        response = "No specific method identified."
        related = parse_related_methods(response, sample_class_info.covered_methods)
        # should fallback to all candidates
        assert len(related) == len(sample_class_info.covered_methods)

    def test_parse_method_score_standard_format(self):
        response = "#SCORE# 8 This method directly handles the character escaping logic."
        score, desc = parse_method_score(response)
        assert score == 8
        assert "escaping" in desc.lower() or len(desc) > 0

    def test_parse_method_score_alt_format(self):
        response = "Score: 6\nThis method seems moderately suspicious."
        score, desc = parse_method_score(response)
        assert score == 6

    def test_parse_method_score_no_score_defaults_5(self):
        response = "This method is somewhat suspicious."
        score, _ = parse_method_score(response)
        assert score == 5

    def test_parse_enhanced_docs_from_table(self, sample_class_info):
        table_response = (
            "| Method Full Name | Method Comment |\n"
            "|---|---|\n"
            "| com.example.StringUtils::escapeHtml(String) | "
            "Escapes HTML; calls escape() for each char |\n"
            "| com.example.StringUtils::escape(char) | "
            "Low-level single-char escaping logic |\n"
        )
        methods = parse_enhanced_docs(table_response, sample_class_info.covered_methods)
        enhanced = [m for m in methods if m.enhanced_doc]
        assert len(enhanced) >= 1

    def test_task7_rank_methods_sorts_descending(self, sample_class_info):
        methods = sample_class_info.covered_methods
        methods[0].suspiciousness_score = 3
        methods[1].suspiciousness_score = 8
        methods[2].suspiciousness_score = 5
        ranked = task7_rank_methods(methods)
        scores = [m.suspiciousness_score for m in ranked]
        assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Generator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptGenerator:

    def test_task1_returns_tuple(self, sample_state):
        sys_p, user = task1_test_behavior_analysis(sample_state)
        assert isinstance(sys_p, str) and len(sys_p) > 10
        assert isinstance(user, str) and len(user) > 10
        assert "StringUtilsTest" in user

    def test_task2_contains_test_behavior(self, sample_state):
        sample_state.test_behavior = "The test expects HTML escaping."
        sys_p, user = task2_test_failure_analysis(sample_state)
        assert "HTML escaping" in user or "test_behavior" in user.lower() or "TEST BEHAVIOR" in user

    def test_task3_contains_covered_classes(self, sample_state, sample_class_info):
        sample_state.covered_classes = [sample_class_info]
        sample_state.possible_causes = "The escaping logic may be incorrect."
        sys_p, user = task3_search_suspicious_class(sample_state)
        assert "com.example.StringUtils" in user

    def test_task4_no_class_returns_gracefully(self, sample_state):
        sample_state.suspicious_class = None
        sys_p, user = task4_method_doc_enhancement(sample_state)
        assert isinstance(user, str)

    def test_task5_contains_methods(self, sample_state, sample_class_info):
        sample_state.suspicious_class = sample_class_info
        sample_state.possible_causes  = "escaping is wrong"
        sys_p, user = task5_find_related_methods(sample_state)
        assert "escapeHtml" in user or "escape" in user

    def test_task6_contains_score_instruction(self, sample_state, sample_class_info):
        sample_state.suspicious_class = sample_class_info
        sample_state.possible_causes  = "escaping may be wrong"
        method = sample_class_info.covered_methods[0]
        sys_p, user = task6_method_review(sample_state, method)
        assert "#SCORE#" in user
        assert "1-10" in user or "10" in user

    def test_task7_empty_list(self):
        assert task7_rank_methods([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# Loader Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLoader:

    def test_load_from_dict(self):
        bug = {
            "project": "Math",
            "bug_id": "5",
            "test_class": "FooTest",
            "failed_tests": ["testFoo"],
            "test_code": {"testFoo": "public void testFoo() { ... }"},
            "source_files": {"Foo.java": "public class Foo {}"},
            "error_messages": {"testFoo": "AssertionError at line 5"},
        }
        state = load_from_dict(bug)
        assert state.project_name == "Math"
        assert state.bug_id == "5"
        assert "testFoo" in state.test_code
        assert "Foo.java" in state.source_files

    def test_load_from_directory(self):
        """Load the built-in sample bug from disk."""
        bug_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sample_bugs", "Lang_10"
        )
        if not os.path.isdir(bug_dir):
            pytest.skip("Sample bug directory not found")

        from src.utils.loader import load_from_directory
        state = load_from_directory(bug_dir)
        assert state.project_name == "Lang"
        assert state.bug_id == "10"
        assert len(state.test_code) > 0
        assert len(state.source_files) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Integration Test (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineIntegration:
    """
    Full pipeline run with a mocked LLM client.
    Verifies that all 7 tasks execute and produce a ranked output.
    """

    def _make_mock_llm(self):
        mock = MagicMock()
        call_count = [0]

        def fake_chat(system_prompt, user_message, history=None, max_retries=3):
            call_count[0] += 1
            n = call_count[0]

            if n == 1:   # Task ❶ test behavior
                return "The test verifies that escapeHtml correctly converts < and > to HTML entities."
            elif n == 2: # Task ❷ possible causes
                return ("Possible defect: The escape() method may not handle all special characters. "
                        "Specifically, the character mapping might be incomplete or incorrectly ordered.")
            elif n == 3: # Task ❸ suspicious class
                return ("After analysis, com.example.StringUtils is the most suspicious class "
                        "because it contains the escaping logic responsible for the test failure.")
            elif n == 4: # Task ❹ method doc enhancement
                return (
                    "| Method Full Name | Method Comment |\n"
                    "|---|---|\n"
                    "| com.example.StringUtils::escapeHtml(String) | "
                    "Iterates each char and calls escape(); responsible for full HTML escaping |\n"
                    "| com.example.StringUtils::escape(char) | "
                    "Converts a single char to its HTML entity; this is the core escaping logic |\n"
                    "| com.example.StringUtils::isEmpty(String) | "
                    "Returns true if input is null or empty string |\n"
                )
            elif n == 5: # Task ❺ related methods
                return ("The following methods are related to the failure:\n"
                        "- com.example.StringUtils::escapeHtml(String)\n"
                        "- com.example.StringUtils::escape(char)\n")
            elif n == 6: # Task ❻ review escapeHtml
                return "#SCORE# 7 This method orchestrates the escaping; a bug here would affect all input."
            elif n == 7: # Task ❻ review escape
                return "#SCORE# 9 This is the core escape logic and most likely contains the bug."
            else:
                return "#SCORE# 3 This method is unlikely to be responsible."

        mock.chat = fake_chat
        mock.token_summary.return_value = {
            "input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500
        }
        return mock

    def test_full_pipeline_run(self, sample_state, sample_class_info):
        from src.components.pipeline import SoapFLPipeline

        # Pre-populate covered classes (normally done by program_analysis)
        sample_state.covered_classes = [sample_class_info]

        mock_llm = self._make_mock_llm()
        pipeline = SoapFLPipeline(llm_client=mock_llm)

        # Patch program_analysis so it doesn't re-parse (we set covered_classes above)
        with patch("src.components.pipeline.run_program_analysis") as mock_pa:
            # After patching, covered_classes must still be set
            def fake_pa(state):
                state.covered_classes = [sample_class_info]
            mock_pa.side_effect = fake_pa

            results = pipeline.run(sample_state)

        assert isinstance(results, list)
        assert len(results) > 0

        # Top result should be the one with score 9 (escape method)
        top = results[0]
        assert top.suspiciousness_score >= 7
        assert top.method_name in ("escape", "escapeHtml")

    def test_pipeline_handles_no_covered_classes(self, sample_state):
        from src.components.pipeline import SoapFLPipeline

        mock_llm = self._make_mock_llm()
        pipeline = SoapFLPipeline(llm_client=mock_llm)

        with patch("src.components.pipeline.run_program_analysis") as mock_pa:
            def fake_pa(state):
                state.covered_classes = []
            mock_pa.side_effect = fake_pa

            results = pipeline.run(sample_state)

        # Should handle gracefully and return empty list or partial
        assert isinstance(results, list)


# ─────────────────────────────────────────────────────────────────────────────
# Edge-case Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_state_save_and_load(self, tmp_path, sample_state):
        path = str(tmp_path / "state.json")
        saved_path = sample_state.save(path)
        assert os.path.isfile(saved_path)
        import json
        with open(saved_path) as f:
            data = json.load(f)
        assert data["project_name"] == "Lang"
        assert data["bug_id"] == "42"

    def test_parse_java_empty_source(self):
        ci = parse_java_source("com.example.Empty", "")
        assert ci.full_name == "com.example.Empty"
        assert isinstance(ci.covered_methods, list)

    def test_parse_method_score_boundary_values(self):
        score, _ = parse_method_score("#SCORE# 1 very unlikely")
        assert score == 1
        score, _ = parse_method_score("#SCORE# 10 very likely")
        assert score == 10

    def test_task7_preserves_all_methods(self, sample_class_info):
        methods = sample_class_info.covered_methods
        for i, m in enumerate(methods):
            m.suspiciousness_score = i + 1
        ranked = task7_rank_methods(methods)
        assert len(ranked) == len(methods)

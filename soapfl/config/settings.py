"""
SOAPFL Configuration Settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq / LLM settings ──────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TEMPERATURE  = float(os.getenv("GROQ_TEMPERATURE", "0"))
MAX_TOKENS   = int(os.getenv("GROQ_MAX_TOKENS", "4096"))

# ── SOAPFL pipeline hyper-parameters ─────────────────────────────────────────
MAX_TEST_OUTPUT_TOKENS  = 200   # cap test-output length fed to LLM
MAX_DOC_TOKENS          = 100   # cap class/method doc length
MAX_FAILED_TESTS        = 5     # max failed test cases per class
TOP_N_RESULTS           = 5     # suspicious methods returned to user
MAX_COVERED_CLASSES     = 30    # max classes shown in search step
MAX_COVERED_METHODS     = 20    # max methods shown in find-methods step

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── LLM role assignments (system prompts) ────────────────────────────────────
ROLES = {
    "test_code_reviewer": (
        "You are a Test Code Reviewer. You are responsible for reviewing test "
        "code and summarizing the test behavior in as much detail as possible."
    ),
    "source_code_reviewer": (
        "You are a Source Code Reviewer. You are responsible for writing "
        "high-quality code comments that accurately describe method functionality "
        "and calling relationships."
    ),
    "software_architect": (
        "You are a Software Architect. You are adept at understanding software "
        "architecture and finding areas of the program that may be problematic."
    ),
    "software_test_engineer": (
        "You are a Software Test Engineer. You are responsible for localizing "
        "the buggy code that causes the test class to fail. Your main "
        "responsibilities include examining the information of the failed tests "
        "to analyze the possible causes of the test failures, and determining "
        "the method that needs to be fixed. To locate the bug, you must write a "
        "response that appropriately solves the requested instruction based on "
        "your expertise."
    ),
}

# SOAPFL — LLM-Based Method-Level Fault Localization

A working Python prototype of the **SOAPFL** system from the IEEE TSE 2025 paper:

> *"SOAPFL: A Standard Operating Procedure for LLM-Based Method-Level Fault Localization"*
> Qin et al., IEEE Transactions on Software Engineering, Vol. 51, No. 4, April 2025.

This implementation uses **Groq API** (instead of OpenAI) as the LLM backend.

---

## Architecture

```
SOAPFL Pipeline (3 Stages, 7 Tasks)
─────────────────────────────────────────────────────────────
Stage 1 │ Fault Comprehension
        │  Task ❶  Test Behavior Analysis   (role: Test Code Reviewer)
        │  Task ❷  Test Failure Analysis    (role: Software Test Engineer)
─────────────────────────────────────────────────────────────
Stage 2 │ Codebase Navigation
        │  Task ❸  Search Suspicious Class  (role: Software Architect)
        │  Task ❹  Method Doc Enhancement   (role: Source Code Reviewer)
        │  Task ❺  Find Related Methods     (role: Software Architect)
─────────────────────────────────────────────────────────────
Stage 3 │ Fault Confirmation
        │  Task ❻  Method Review (multi-round, 1 method per call)
        │  Task ❼  Suspicious Method Ranking (pure Python, no LLM)
─────────────────────────────────────────────────────────────
```

Supporting components:
- **Program Analysis** — static Java source parser + simulated test-behavior tracking
- **State Storage** — typed dataclasses for all intermediate pipeline data
- **Result Parser** — extracts structured data from raw LLM text
- **Prompt Generator** — builds role-specific prompts for all 7 tasks

---

## Project Structure

```
soapfl/
├── main.py                          # CLI entry point
├── requirements.txt
├── .env.example                     # copy to .env and add your Groq key
├── conftest.py
│
├── config/
│   ├── __init__.py
│   └── settings.py                  # all tunable hyper-parameters
│
├── src/
│   ├── __init__.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── llm_client.py            # Groq API wrapper with retry + token tracking
│   │   ├── state_storage.py         # PipelineState, ClassInfo, MethodInfo dataclasses
│   │   ├── program_analysis.py      # static analysis + test-utility tracking
│   │   ├── result_parser.py         # LLM response → structured data
│   │   └── pipeline.py              # SoapFLPipeline orchestrator (7 tasks)
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── prompt_generator.py      # all 7 task prompt templates
│   └── utils/
│       ├── __init__.py
│       ├── loader.py                # load bug from directory or dict
│       └── report.py                # terminal output + JSON result file
│
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py             # full pytest test suite (mocked LLM)
│   └── sample_bugs/
│       └── Lang_10/                 # sample Defects4J-style bug (Lang bug #10)
│           ├── bug.json
│           ├── tests/
│           │   └── FastDateFormatTest.java
│           ├── src/
│           │   └── org/apache/commons/lang3/
│           │       ├── FastDateParser.java   ← contains deliberate bugs
│           │       └── FastDateFormat.java
│           └── errors/
│               ├── testFormat.txt
│               └── testDateTimeInstance.txt
│
└── output/                          # auto-created; JSON result files saved here
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install groq javalang python-dotenv rich pytest
```

### 2. Set up your Groq API key

```bash
cp .env.example .env
# edit .env and add your key:
# GROQ_API_KEY=gsk_...
```

Get a free key at https://console.groq.com

### 3. Run on the built-in sample bug

```bash
python main.py
```

### 4. Run on your own bug

Create a directory following this layout:

```
my_bug/
├── bug.json          ← metadata
├── tests/            ← failing test .java files
├── src/              ← production .java source files
└── errors/           ← stack trace .txt files (one per test)
```

`bug.json` format:
```json
{
  "project": "MyProject",
  "bug_id": "42",
  "test_class": "MyFailingTest",
  "failed_tests": ["testFoo", "testBar"]
}
```

Then run:
```bash
python main.py --bug-dir path/to/my_bug
```

### 5. Programmatic usage

```python
from src.utils.loader import load_from_dict
from src.components.pipeline import SoapFLPipeline
from src.utils.report import print_results, save_results
import time

bug = {
    "project": "Lang",
    "bug_id": "42",
    "test_class": "StringUtilsTest",
    "failed_tests": ["testEscapeHtml"],
    "test_code": {"StringUtilsTest": "... java source ..."},
    "source_files": {"StringUtils.java": "... java source ..."},
    "error_messages": {"testEscapeHtml": "AssertionError at line 22"},
}

state    = load_from_dict(bug)
pipeline = SoapFLPipeline()      # reads GROQ_API_KEY from .env

t0      = time.time()
results = pipeline.run(state)
elapsed = time.time() - t0

print_results(state, results, elapsed, pipeline.llm.token_summary())
save_results(state, results, elapsed, pipeline.llm.token_summary())
```

---

## Configuration

All tunable parameters live in `config/settings.py`:

| Parameter | Default | Description |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `TEMPERATURE` | `0` | LLM temperature (0 = deterministic) |
| `MAX_TOKENS` | `4096` | Max tokens per LLM call |
| `MAX_FAILED_TESTS` | `5` | Max failed test cases per run |
| `TOP_N_RESULTS` | `5` | Suspicious methods in final output |
| `MAX_COVERED_CLASSES` | `30` | Max classes shown in Search step |
| `MAX_COVERED_METHODS` | `20` | Max methods shown in Find-Methods step |

### Recommended Groq models

| Model | Speed | Quality |
|---|---|---|
| `llama-3.3-70b-versatile` | Fast | Best (recommended) |
| `llama-3.1-70b-versatile` | Fast | Very good |
| `mixtral-8x7b-32768` | Fastest | Good |

---

## Running Tests

Tests run without a real Groq API key (LLM is mocked):

```bash
# with pytest
pytest tests/test_pipeline.py -v

# with unittest (no pytest needed)
python -m unittest tests.test_pipeline -v
```

Tests cover:
- All 7 prompt templates (correct roles, content, format)
- Program analysis (Java parsing, class intersection, utility tracking)
- Result parser (class extraction, method extraction, score parsing, doc tables)
- Loader (directory and dict modes)
- Full pipeline integration (mocked LLM, correct ranking)
- Edge cases (empty inputs, missing files, boundary scores)

---

## Output

For each bug, SOAPFL writes two files to `output/`:

- `<project>_<bug_id>_result.json` — ranked suspicious methods with rationale
- `<project>_<bug_id>_state.json` — full pipeline state (all 7 task outputs)

Example `result.json`:
```json
{
  "project": "Lang",
  "bug_id": "10",
  "suspicious_class": "org.apache.commons.lang3.time.FastDateParser",
  "suspicious_methods": [
    {
      "rank": 1,
      "score": 9,
      "method": "org.apache.commons.lang3.time.FastDateParser::buildRegex(String)",
      "reason": "Does not escape special regex characters, causing Pattern.compile to fail."
    },
    ...
  ],
  "cost": {
    "elapsed_seconds": 12.4,
    "input_tokens": 4800,
    "output_tokens": 1200,
    "total_tokens": 6000
  }
}
```

---

## Paper vs Prototype Differences

| Feature | Paper (SOAPFL) | This Prototype |
|---|---|---|
| LLM backend | GPT-3.5-turbo-16k | Groq (llama-3.3-70b) |
| Dynamic instrumentation | JVM agent (bytecode) | Simulated via import/call heuristics |
| Java parsing | tree-sitter | javalang + regex fallback |
| Benchmark | Defects4J V1.2.0 (395 bugs) | Any bug directory / custom input |
| Framework | ChatDev | Pure Python |

All three SOAPFL stages and all 7 tasks are faithfully implemented.

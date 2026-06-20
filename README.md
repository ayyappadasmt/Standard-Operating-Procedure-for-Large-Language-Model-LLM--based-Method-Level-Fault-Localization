
# SOAPFL: LLM-Based Method-Level Fault Localization

SOAPFL is an implementation of the methodology proposed in the paper:

> **SOAPFL: A Standard Operating Procedure for LLM-Based Method-Level Fault Localization**
> Qin et al., IEEE Transactions on Software Engineering (TSE), 2025

This project reproduces the **SOAPFL pipeline** for automated fault localization using Large Language Models, static program analysis, and structured reasoning.

Unlike the original implementation that utilizes OpenAI models, this implementation uses the **Groq API** as the inference backend.

---

## Overview

Software fault localization is a challenging and time-consuming task in software maintenance.

SOAPFL addresses this problem by decomposing fault localization into a sequence of reasoning tasks that guide an LLM through:

* Understanding failing tests
* Analyzing stack traces
* Navigating the codebase
* Reviewing suspicious methods
* Ranking potential buggy methods

The framework combines:

* LLM reasoning
* Static Java source analysis
* Prompt engineering
* Multi-stage fault confirmation
* Structured state management

---

## SOAPFL Architecture
<p align="center">
  <img src="https://github.com/user-attachments/assets/b195037c-232b-410f-8f1f-153cd4232796"
       width="425"
       alt="StarDust Interface">
  <br>
  
</p>

The SOAPFL pipeline consists of **3 stages and 7 tasks**.

### Stage 1 – Fault Comprehension

#### Task 1: Test Behavior Analysis
Role:
> Test Code Reviewer

Analyzes failing test cases and summarizes expected behavior.

#### Task 2: Test Failure Analysis
Role:
> Software Test Engineer

Examines failure logs and infers possible root causes.

---

### Stage 2 – Codebase Navigation

#### Task 3: Search Suspicious Classes
Role:
> Software Architect

Identifies classes likely associated with the fault.


#### Task 4: Method Documentation Enhancement
Role:
> Source Code Reviewer

Generates richer descriptions for methods.


#### Task 5: Find Related Methods
Role:
> Software Architect

Discovers methods potentially involved in the defect.


---

### Stage 3 – Fault Confirmation

#### Task 6: Method Review

Performs iterative inspection of suspicious methods.


#### Task 7: Suspicious Method Ranking

Ranks candidate methods according to estimated fault likelihood.


---

## Features

- Implementation of the complete SOAPFL workflow
- Groq-powered LLM backend
- Static Java source code parsing
- Defects4J-style dataset support
- Prompt templates for all seven SOAPFL tasks
- Structured pipeline state management
- Token usage tracking
- JSON result generation
- Rich terminal logging
- Pytest-based testing support


---

## Project Structure

```text
soapfl/
│
├── main.py
├── requirements.txt
├── config/
│   └── settings.py
│
├── src/
│   ├── components/
│   │   ├── llm_client.py
│   │   ├── pipeline.py
│   │   ├── program_analysis.py
│   │   ├── result_parser.py
│   │   └── state_storage.py
│   │
│   ├── prompts/
│   │   └── prompt_generator.py
│   │
│   └── utils/
│       ├── loader.py
│       └── report.py
│
├── tests/
│   ├── test_pipeline.py
│   └── sample_bugs/
│       └── Lang_10/
│
└── output/
```

---

## Tech Stack

| Component | Technology |
|----------|------------|
| Language | Python 3 |
| LLM Backend | Groq API |
| Models | Llama 3.3 70B |
| Java Parsing | javalang |
| Environment | python-dotenv |
| Logging | Rich |
| Testing | Pytest |

---

## Installation

Clone the repository.

```bash
git clone https://github.com/ayyappadasmt/soapfl_1.git

cd soapfl_1/soapfl
```


Install dependencies.


```bash
pip install -r requirements.txt
```


---

## Environment Setup

Create a `.env` file.


Example:


```env
GROQ_API_KEY=your_api_key

GROQ_MODEL=llama-3.3-70b-versatile

GROQ_TEMPERATURE=0

GROQ_MAX_TOKENS=4096
```


Obtain a Groq API key from:

https://console.groq.com


---

## Running SOAPFL


### Run the sample defect


```bash
python main.py
```



### Run a custom defect


```bash
python main.py --bug-dir path/to/bug
```



Example:


```bash
python main.py --bug-dir tests/sample_bugs/Lang_10
```



---

## Expected Input Format


SOAPFL expects a Defects4J-style directory structure.


```text
my_bug/

├── bug.json

├── src/

├── tests/

└── errors/
```



### bug.json


Contains metadata describing the defect.



### src/

Production Java source files.



### tests/

Failing test cases.



### errors/

Failure logs and stack traces.



---

## Outputs


SOAPFL automatically generates:


* Ranked suspicious methods
* Pipeline execution statistics
* Token consumption summary
* JSON result files
* Serialized pipeline state



Generated files are stored inside:


```text
output/
```



Example:


```text
Lang_10_result.json

Lang_10_state.json
```



---

## Testing


Run the test suite.


```bash
pytest
```



---

## Sample Dataset


A sample Defects4J-inspired bug is included:


```text
tests/sample_bugs/Lang_10/
```



This dataset contains:


* Java source files
* Failing tests
* Error traces
* Bug metadata



---

## Research Background


This implementation follows the methodology proposed in:


> Qin et al.
>
> **SOAPFL: A Standard Operating Procedure for LLM-Based Method-Level Fault Localization**
>
> IEEE Transactions on Software Engineering
>
> Volume 51, Issue 4, 2025


---

## Future Improvements


Potential extensions include:


- Support for additional LLM providers
- Integration with Defects4J benchmarks
- Retrieval-Augmented Generation (RAG)
- Interactive visualization dashboard
- Automated patch generation
- Multi-language support


---

## Contributors

**Abhinav Dileep**
**Ayyappa Das M T**
**Hari Sankar A**
**Parthiv M**

GitHub:
https://github.com/ayyappadasmt


---

## License


This project is intended for research and educational purposes.

Please cite the original SOAPFL paper when using this implementation in academic work.

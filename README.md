# AI Test Intelligence Pipeline

> A multi-agent AI workflow that converts software requirements into a structured test plan, classified test cases, and Appium automation scripts — with human review gates at every critical decision point.

---

## Architecture

```
Requirements Input (text / file / URL)
           │
           ▼
   ┌───────────────┐
   │   Agent 1     │  ← Analyses requirements
   │  Test Plan    │    Identifies scope, risks, coverage matrix
   └───────┬───────┘
           │
           ▼
   ┌───────────────────────────────┐
   │  Human Review Gate 1          │  ← QA Lead approves or rejects
   │  (Streamlit UI / CLI)         │    Rejection triggers revision loop
   └───────────────┬───────────────┘
           approved│
           ▼
   ┌───────────────┐
   │   Agent 2     │  ← Generates test cases with steps & preconditions
   │  Test Cases   │    Tags each as manual | automate | hybrid
   └───────┬───────┘    Persists all cases to outputs/test_cases.json
           │
           │ automate-tagged cases only
           ▼
   ┌───────────────┐
   │   Agent 3     │  ← Reads repo context (page objects, helpers)
   │  Automation   │    Generates Appium + pytest scripts
   │   Scripts     │    Includes Zephyr case linkage
   └───────┬───────┘
           │
           ▼
   ┌───────────────────────────────┐
   │  Human Review Gate 2          │  ← Engineer checks selector accuracy
   │  (Streamlit UI / CLI)         │    & pattern compliance
   └───────────────┬───────────────┘
           approved│
           ▼
   PR-ready script files + traceability matrix
   (requirements → test cases → scripts → Zephyr)
```

### Agent Responsibilities

| Agent | Input | Output | Review Gate |
|-------|-------|--------|-------------|
| Agent 1 | Requirements text | Structured test plan (JSON) | Gate 1 — QA Lead |
| Agent 2 | Approved test plan | Classified test cases (JSON) | None (automatic) |
| Agent 3 | Automate-tagged cases + repo context | Appium pytest scripts | Gate 2 — Engineer |

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | Anthropic Claude (claude-sonnet-4) | Excellent structured JSON output; reliable instruction-following for test engineering tasks |
| Orchestration | LangGraph | Native support for stateful multi-agent graphs, revision loops, and conditional edges without boilerplate |
| Human Review UI | Streamlit | Fastest path to a polished, shareable web UI; ideal for demo recordings |
| Test Framework | Appium + pytest | Industry standard for mobile automation; page object pattern is well-understood |
| Test Store | JSON files (outputs/) | Simple, portable, no external dependency — real deployment would use Zephyr API |
| Language | Python 3.11+ | Best LLM/LangGraph ecosystem support |

---

## Project Structure

```
ai-test-pipeline/
├── app.py                        # Streamlit web UI (main entry point)
├── orchestrator.py               # LangGraph pipeline + CLI runner
├── requirements.txt
├── .env.example
├── agents/
│   ├── agent1_test_plan.py       # Agent 1 — test plan generation
│   ├── agent2_test_cases.py      # Agent 2 — test case generation + classification
│   └── agent3_automation.py     # Agent 3 — Appium script generation
├── utils/
│   └── models.py                 # Pydantic models + LangGraph PipelineState TypedDict
├── sample_inputs/
│   └── requirements.txt          # Sample mobile app requirements
└── outputs/                      # Generated artefacts (git-ignored)
    ├── test_plan.json
    ├── test_cases.json
    ├── automation_scripts.json
    ├── pipeline_summary.json
    └── scripts/
        └── test_*.py
```

---

## Setup & Running

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/ai-test-pipeline.git
cd ai-test-pipeline
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3a. Run the Streamlit UI (recommended)

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser. You can enter your API key directly in the UI.

### 3b. Run the CLI version

```bash
python orchestrator.py
```

The CLI runs the pipeline step-by-step and prompts you for approval/rejection at each review gate.

---

## Prompt Engineering Approach

Each agent uses a **structured output system prompt** that:

1. Defines the agent's role and expertise ("You are a senior QA architect...")
2. Specifies the exact JSON schema the output must match
3. States classification rules explicitly (for Agent 2)
4. Includes repo context injection (for Agent 3) so scripts are grounded in real page objects

Revision loops work by appending the reviewer's feedback to the next prompt:
```
PREVIOUS OUTPUT WAS REJECTED. Reviewer feedback:
<feedback text>

Please revise to address the above...
```

This "feedback-in-context" approach is simpler and more reliable than fine-tuning or RAG for iterative correction.

---

## Sample Outputs

### Test Plan (excerpt)
```json
{
  "title": "Mobile Login & Onboarding — Test Plan v1",
  "scope": "Authentication flows (email/password, OAuth), session management, new user onboarding",
  "risk_areas": [
    "Account lockout after failed attempts",
    "OAuth token handling across providers",
    "Biometric re-auth edge cases"
  ],
  "coverage_matrix": [
    { "area": "Happy path login", "priority": "high", "notes": "Core regression blocker" },
    { "area": "Invalid credentials", "priority": "high", "notes": "Security-critical" }
  ]
}
```

### Test Case (excerpt)
```json
{
  "id": "TC-003",
  "title": "Account locks after 5 failed login attempts",
  "classification": "automate",
  "classification_reason": "Deterministic, data-driven, regression-critical — ideal for automation",
  "priority": "high",
  "steps": [
    { "step_number": 1, "action": "Launch app", "expected": "Login screen displayed" },
    { "step_number": 2, "action": "Enter incorrect password 5 times", "expected": "Error message shown each time" },
    { "step_number": 3, "action": "Attempt 6th login", "expected": "Account locked message displayed" }
  ]
}
```

### Automation Script (excerpt)
```python
"""
Test Case: TC-003 — Account locks after 5 failed login attempts
Zephyr Link: ZEPHYR-TC-003
"""
import pytest
from pages.login_page import LoginPage

@pytest.mark.parametrize("attempt", range(1, 6))
def test_failed_login_attempt(driver, attempt):
    login_page = LoginPage(driver)
    login_page.enter_email("user@test.com")
    login_page.enter_password("WrongPassword!")
    login_page.tap_login_button()
    assert login_page.is_error_displayed(), f"No error on attempt {attempt}"

def test_account_locked_after_five_failures(driver):
    login_page = LoginPage(driver)
    for _ in range(5):
        login_page.enter_email("user@test.com")
        login_page.enter_password("WrongPassword!")
        login_page.tap_login_button()
    login_page.enter_password("WrongPassword!")
    login_page.tap_login_button()
    assert "locked" in login_page.get_error_text().lower(), "Expected account locked message"
```

---

## Challenges & Decisions

### 1. LangGraph vs custom orchestration
LangGraph's `StateGraph` made revision loops trivial — a conditional edge reads `plan_approved` and routes back to `agent1` automatically. A custom solution would have needed manual loop management.

### 2. Structured JSON output reliability
Claude is reliable at following JSON schemas in system prompts, but the code strips markdown fences defensively before parsing. In production, using `response_format={"type": "json_object"}` would be the cleaner approach.

### 3. Stateless agents in a stateful graph
Each agent function is pure: it takes `PipelineState` and returns an updated copy. This made testing each agent in isolation easy and avoids shared mutable state bugs.

### 4. Mock vs real Zephyr integration
The Zephyr link (`ZEPHYR-TC-001`) is currently a generated stub. The real implementation would call the Zephyr Scale REST API (`POST /testcases`) to create the case and return the real key.

---

## What I'd Improve with More Time

- **Real Zephyr API integration** — create cases via API and link script commits back to test executions
- **Confluence requirements ingestion** — Agent 1 would fetch pages via Confluence REST API rather than pasting text
- **CI/CD hook** — GitHub Actions workflow that triggers Agent 1 whenever a Confluence page with `[QA-REQUIRED]` label is updated
- **Vector store for repo context** — embed the full test repo and retrieve relevant page objects per test case rather than injecting the entire context
- **Parallel test case generation** — Agent 2 could fan out across coverage areas in parallel, reducing latency for large test plans
- **Confidence scoring** — Agent 3 flags selectors it's uncertain about for mandatory human review rather than routing all scripts to a single gate

---

## Deliverables Checklist

- [x] Working prototype — functional multi-agent pipeline with end-to-end run
- [x] Architecture diagram — agent orchestration, data flow, integration points
- [x] Technical write-up (this README)
- [x] Sample outputs — test_plan.json, test_cases.json, automation script stubs
- [ ] Demo video — record 5-10 min Loom walkthrough of the Streamlit UI

---

## License

MIT

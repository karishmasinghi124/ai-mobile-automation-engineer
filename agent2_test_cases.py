"""
Agent 2 — Test Case Generator

Takes an approved test plan and generates individual test cases with
steps, expected results, preconditions, and classification tags:
  manual | automate | hybrid

Pushes all cases to a JSON test store and routes automate-tagged
cases to Agent 3.
"""
import json
import os
from pathlib import Path
import anthropic
from utils.models import PipelineState

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a senior QA engineer specialising in mobile test case design.
Given an approved test plan, generate a comprehensive set of individual test cases.

ALWAYS respond with a valid JSON array of test case objects (no markdown, no extra text).
Each object must match this exact schema:
[
  {
    "id": "TC-001",
    "title": "string — concise test case title",
    "preconditions": ["string", ...],
    "steps": [
      {"step_number": 1, "action": "string", "expected": "string"},
      ...
    ],
    "expected_result": "string — overall pass condition",
    "classification": "manual | automate | hybrid",
    "classification_reason": "string — why this classification",
    "priority": "high | medium | low",
    "tags": ["string", ...]
  },
  ...
]

Classification rules:
- automate: repetitive, data-driven, regression-critical, or UI-interaction-heavy cases
- manual: exploratory, UX/feel judgement, one-off edge cases, accessibility reviews
- hybrid: partially automatable steps with manual validation checkpoints

Generate enough cases to give high coverage — aim for 10-15 cases minimum.
"""


def run_agent2(state: PipelineState) -> PipelineState:
    """
    Node function for LangGraph. Generates and classifies test cases.
    """
    test_plan = state["test_plan"]
    requirements = state["requirements_text"]

    user_message = f"""REQUIREMENTS (for context):
{requirements}

APPROVED TEST PLAN:
{json.dumps(test_plan, indent=2)}

Generate a comprehensive set of test cases covering all areas in the coverage matrix.
Make sure to include positive, negative, edge case, and non-functional test cases.
"""

    print(f"\n{'='*60}")
    print("[Agent 2] Generating test cases from approved test plan...")
    print(f"{'='*60}")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    test_cases = json.loads(raw)

    # Split by classification
    automate_cases = [tc for tc in test_cases if tc["classification"] == "automate"]
    manual_cases = [tc for tc in test_cases if tc["classification"] in ("manual", "hybrid")]

    # Persist to JSON store
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    (output_dir / "test_cases.json").write_text(
        json.dumps(test_cases, indent=2), encoding="utf-8"
    )

    print(f"[Agent 2] ✅ Generated {len(test_cases)} test cases:")
    print(f"  • {len(automate_cases)} to automate")
    print(f"  • {len(manual_cases)} manual/hybrid")
    print(f"  • Saved to outputs/test_cases.json")

    return {
        **state,
        "test_cases": test_cases,
        "automate_cases": automate_cases,
        "manual_cases": manual_cases,
        "current_stage": "agent3" if automate_cases else "complete",
    }


def generate_test_cases_direct(test_plan: dict, requirements: str) -> list:
    """
    Standalone call used by Streamlit UI.
    Returns the list of test case dicts.
    """
    state: PipelineState = {
        "requirements_text": requirements,
        "repo_context": "",
        "test_plan": test_plan,
        "test_plan_revision_count": 1,
        "test_plan_feedback": None,
        "test_cases": None,
        "automate_cases": None,
        "manual_cases": None,
        "automation_scripts": None,
        "scripts_revision_count": 0,
        "scripts_feedback": None,
        "plan_approved": True,
        "scripts_approved": None,
        "current_stage": "agent2",
        "error_message": None,
        "run_id": "direct",
    }
    result = run_agent2(state)
    return result["test_cases"]

"""
Agent 1 — Test Plan Generator

Accepts requirement inputs, aggregates context, and outputs a structured
test plan for human review. Supports revision loops when rejected.
"""
import json
import os
import anthropic
from utils.models import PipelineState

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a senior QA architect specialising in mobile test strategy.
Your job is to analyse software requirements and produce a thorough, structured test plan.

ALWAYS respond with a valid JSON object that matches this exact schema (no markdown, no extra text):
{
  "title": "string — descriptive plan title",
  "scope": "string — what is covered",
  "risk_areas": ["string", ...],
  "coverage_matrix": [
    {"area": "string", "priority": "high|medium|low", "notes": "string"},
    ...
  ],
  "out_of_scope": ["string", ...],
  "assumptions": ["string", ...]
}

Be thorough: identify security, performance, accessibility, and UX risks alongside functional coverage.
"""


def run_agent1(state: PipelineState) -> PipelineState:
    """
    Node function for LangGraph. Generates (or revises) a test plan.
    """
    requirements = state["requirements_text"]
    feedback = state.get("test_plan_feedback")
    revision_count = state.get("test_plan_revision_count", 0)

    # Build the user message — include feedback if this is a revision
    if feedback and revision_count > 0:
        user_message = f"""REQUIREMENTS:
{requirements}

PREVIOUS PLAN WAS REJECTED. Reviewer feedback:
{feedback}

Please revise the test plan to address the feedback above. Keep what was correct and improve the flagged areas.
"""
    else:
        user_message = f"""Please generate a comprehensive test plan for the following requirements:

{requirements}
"""

    print(f"\n{'='*60}")
    print(f"[Agent 1] Generating test plan (revision #{revision_count})...")
    print(f"{'='*60}")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    test_plan = json.loads(raw)

    print(f"[Agent 1] ✅ Test plan generated: '{test_plan['title']}'")
    print(f"  • {len(test_plan['risk_areas'])} risk areas identified")
    print(f"  • {len(test_plan['coverage_matrix'])} coverage areas")

    return {
        **state,
        "test_plan": test_plan,
        "test_plan_revision_count": revision_count + 1,
        "plan_approved": None,
        "current_stage": "human_review_1",
    }


def generate_test_plan_direct(requirements: str, feedback: str = None, revision: int = 0) -> dict:
    """
    Standalone call used by Streamlit UI.
    Returns the test plan dict.
    """
    state: PipelineState = {
        "requirements_text": requirements,
        "repo_context": "",
        "test_plan": None,
        "test_plan_revision_count": revision,
        "test_plan_feedback": feedback,
        "test_cases": None,
        "automate_cases": None,
        "manual_cases": None,
        "automation_scripts": None,
        "scripts_revision_count": 0,
        "scripts_feedback": None,
        "plan_approved": None,
        "scripts_approved": None,
        "current_stage": "agent1",
        "error_message": None,
        "run_id": "direct",
    }
    result = run_agent1(state)
    return result["test_plan"]

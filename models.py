"""
Shared state models and types for the AI Test Intelligence Pipeline.
"""
from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel


# ─── Pydantic models for structured agent outputs ───────────────────────────

class CoverageItem(BaseModel):
    area: str
    priority: Literal["high", "medium", "low"]
    notes: str


class TestPlan(BaseModel):
    title: str
    scope: str
    risk_areas: List[str]
    coverage_matrix: List[CoverageItem]
    out_of_scope: List[str]
    assumptions: List[str]


class TestStep(BaseModel):
    step_number: int
    action: str
    expected: str


class TestCase(BaseModel):
    id: str
    title: str
    preconditions: List[str]
    steps: List[TestStep]
    expected_result: str
    classification: Literal["manual", "automate", "hybrid"]
    classification_reason: str
    priority: Literal["high", "medium", "low"]
    tags: List[str]


class AutomationScript(BaseModel):
    test_case_id: str
    test_case_title: str
    framework: str
    file_path: str
    script_content: str
    page_objects_used: List[str]
    zephyr_link: str


# ─── LangGraph pipeline state ────────────────────────────────────────────────

class PipelineState(TypedDict):
    # Inputs
    requirements_text: str
    repo_context: str

    # Agent 1 outputs
    test_plan: Optional[dict]
    test_plan_revision_count: int
    test_plan_feedback: Optional[str]

    # Agent 2 outputs
    test_cases: Optional[List[dict]]
    automate_cases: Optional[List[dict]]
    manual_cases: Optional[List[dict]]

    # Agent 3 outputs
    automation_scripts: Optional[List[dict]]
    scripts_revision_count: int
    scripts_feedback: Optional[str]

    # Review gate decisions
    plan_approved: Optional[bool]
    scripts_approved: Optional[bool]

    # Pipeline status
    current_stage: str
    error_message: Optional[str]
    run_id: str

"""
LangGraph Orchestrator — AI Test Intelligence Pipeline

Wires all three agents + two human review gates into a stateful graph:

  requirements_input
       │
       ▼
  [agent1_node] ──► [human_review_1_node]
       ▲                    │
       │  rejected          │ approved
       └────────────────────┘
                            │
                            ▼
                    [agent2_node]
                            │
                            ▼ (automate cases only)
                    [agent3_node] ──► [human_review_2_node]
                       ▲                    │
                       │  rejected          │ approved
                       └────────────────────┘
                                            │
                                            ▼
                                      [complete]
"""
import uuid
import json
from pathlib import Path

from langgraph.graph import StateGraph, END
from agents.agent1_test_plan import run_agent1
from agents.agent2_test_cases import run_agent2
from agents.agent3_automation import run_agent3
from utils.models import PipelineState


# ─── Human Review Gate Nodes ─────────────────────────────────────────────────

def human_review_1_node(state: PipelineState) -> PipelineState:
    """
    Placeholder node — the actual review decision is injected externally
    (by the Streamlit UI or CLI). This node just passes state through.
    The graph router reads state['plan_approved'] to decide the next edge.
    """
    return {**state, "current_stage": "awaiting_plan_review"}


def human_review_2_node(state: PipelineState) -> PipelineState:
    """
    Placeholder node for scripts review.
    """
    return {**state, "current_stage": "awaiting_scripts_review"}


def complete_node(state: PipelineState) -> PipelineState:
    """Final node — saves summary output."""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    summary = {
        "run_id": state["run_id"],
        "test_plan": state.get("test_plan"),
        "total_test_cases": len(state.get("test_cases") or []),
        "automate_count": len(state.get("automate_cases") or []),
        "manual_count": len(state.get("manual_cases") or []),
        "script_files": [
            {"case_id": s["test_case_id"], "file": s["file_path"], "zephyr": s["zephyr_link"]}
            for s in (state.get("automation_scripts") or [])
        ],
    }
    (output_dir / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETE")
    print(f"  • Test cases: {summary['total_test_cases']}")
    print(f"  • Automate:   {summary['automate_count']}")
    print(f"  • Manual:     {summary['manual_count']}")
    print(f"  • Scripts:    {len(summary['script_files'])}")
    print("  • Summary:    outputs/pipeline_summary.json")
    print("="*60)

    return {**state, "current_stage": "complete"}


# ─── Edge Router Functions ────────────────────────────────────────────────────

def route_after_plan_review(state: PipelineState) -> str:
    """After human review gate 1, route based on approval decision."""
    if state.get("plan_approved") is True:
        return "agent2"
    elif state.get("plan_approved") is False:
        return "agent1"  # revision loop
    else:
        return "human_review_1"  # still waiting


def route_after_scripts_review(state: PipelineState) -> str:
    """After human review gate 2, route based on approval decision."""
    if state.get("scripts_approved") is True:
        return "complete"
    elif state.get("scripts_approved") is False:
        return "agent3"  # revision loop
    else:
        return "human_review_2"  # still waiting


def route_after_agent2(state: PipelineState) -> str:
    """After Agent 2, go to Agent 3 only if there are cases to automate."""
    if state.get("automate_cases"):
        return "agent3"
    return "complete"


# ─── Build the LangGraph ─────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("agent1", run_agent1)
    graph.add_node("human_review_1", human_review_1_node)
    graph.add_node("agent2", run_agent2)
    graph.add_node("agent3", run_agent3)
    graph.add_node("human_review_2", human_review_2_node)
    graph.add_node("complete", complete_node)

    # Entry point
    graph.set_entry_point("agent1")

    # Edges
    graph.add_edge("agent1", "human_review_1")

    graph.add_conditional_edges(
        "human_review_1",
        route_after_plan_review,
        {
            "agent1": "agent1",
            "agent2": "agent2",
            "human_review_1": "human_review_1",
        }
    )

    graph.add_conditional_edges(
        "agent2",
        route_after_agent2,
        {
            "agent3": "agent3",
            "complete": "complete",
        }
    )

    graph.add_edge("agent3", "human_review_2")

    graph.add_conditional_edges(
        "human_review_2",
        route_after_scripts_review,
        {
            "agent3": "agent3",
            "complete": "complete",
            "human_review_2": "human_review_2",
        }
    )

    graph.add_edge("complete", END)

    return graph.compile()


# ─── CLI runner ───────────────────────────────────────────────────────────────

def run_cli(requirements_text: str, repo_context: str = "") -> None:
    """
    CLI runner with interactive human review prompts.
    """
    pipeline = build_pipeline()

    initial_state: PipelineState = {
        "requirements_text": requirements_text,
        "repo_context": repo_context,
        "test_plan": None,
        "test_plan_revision_count": 0,
        "test_plan_feedback": None,
        "test_cases": None,
        "automate_cases": None,
        "manual_cases": None,
        "automation_scripts": None,
        "scripts_revision_count": 0,
        "scripts_feedback": None,
        "plan_approved": None,
        "scripts_approved": None,
        "current_stage": "start",
        "error_message": None,
        "run_id": str(uuid.uuid4())[:8],
    }

    state = initial_state

    # Manual step-through for CLI (LangGraph streaming mode)
    for step_output in pipeline.stream(state, stream_mode="values"):
        state = step_output
        stage = state.get("current_stage")

        if stage == "awaiting_plan_review":
            print("\n" + "─"*60)
            print("📋 HUMAN REVIEW GATE 1 — Test Plan Review")
            print("─"*60)
            print(json.dumps(state["test_plan"], indent=2))
            print("─"*60)
            decision = input("\nApprove this test plan? [y/n]: ").strip().lower()
            if decision == "y":
                state["plan_approved"] = True
                state["test_plan_feedback"] = None
            else:
                feedback = input("Enter your feedback for Agent 1: ").strip()
                state["plan_approved"] = False
                state["test_plan_feedback"] = feedback

        elif stage == "awaiting_scripts_review":
            print("\n" + "─"*60)
            print("🔍 HUMAN REVIEW GATE 2 — Script Review")
            print("─"*60)
            for script in state.get("automation_scripts", []):
                print(f"\n--- {script['file_path']} [{script['test_case_id']}] ---")
                print(script["script_content"][:500] + "..." if len(script["script_content"]) > 500 else script["script_content"])
            print("─"*60)
            decision = input("\nApprove these scripts? [y/n]: ").strip().lower()
            if decision == "y":
                state["scripts_approved"] = True
                state["scripts_feedback"] = None
            else:
                feedback = input("Enter your feedback for Agent 3: ").strip()
                state["scripts_approved"] = False
                state["scripts_feedback"] = feedback


if __name__ == "__main__":
    from pathlib import Path
    reqs = Path("sample_inputs/requirements.txt").read_text()
    run_cli(reqs)

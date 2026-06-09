"""
Streamlit Web UI — AI Test Intelligence Pipeline

A clean, professional review interface that:
- Accepts requirements input (text or file upload)
- Runs each agent and shows live output
- Presents Human Review Gates as interactive approval/rejection forms
- Displays test cases in a filterable table
- Shows generated scripts with syntax highlighting
- Produces a final traceability summary

Run with: streamlit run app.py
"""
import json
import os
import time
import uuid
from pathlib import Path

import streamlit as st

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Test Intelligence Pipeline",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Clean dark-accent palette */
  :root {
    --primary: #2563EB;
    --success: #16A34A;
    --warning: #D97706;
    --danger: #DC2626;
    --surface: #F8FAFC;
    --border: #E2E8F0;
  }

  .agent-card {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-left: 4px solid var(--primary);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
  }
  .agent-card.success { border-left-color: var(--success); }
  .agent-card.warning { border-left-color: var(--warning); }
  .agent-card.pending { border-left-color: #94A3B8; }

  .review-banner {
    background: #FEF9C3;
    border: 1px solid #FDE68A;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
    font-weight: 600;
    color: #92400E;
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .badge-automate { background: #DBEAFE; color: #1E40AF; }
  .badge-manual   { background: #D1FAE5; color: #065F46; }
  .badge-hybrid   { background: #FEF3C7; color: #92400E; }
  .badge-high     { background: #FEE2E2; color: #991B1B; }
  .badge-medium   { background: #FEF9C3; color: #92400E; }
  .badge-low      { background: #F0FDF4; color: #166534; }

  .stat-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
  }
  .stat-box .num { font-size: 2rem; font-weight: 800; color: var(--primary); }
  .stat-box .lbl { font-size: 0.8rem; color: #64748B; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


# ─── Session state initialisation ─────────────────────────────────────────────
def init_state():
    defaults = {
        "stage": "input",          # input | agent1 | review1 | agent2 | agent3 | review2 | complete
        "run_id": str(uuid.uuid4())[:8],
        "requirements": "",
        "test_plan": None,
        "plan_revision": 0,
        "plan_feedback": None,
        "test_cases": [],
        "automate_cases": [],
        "manual_cases": [],
        "scripts": [],
        "scripts_revision": 0,
        "scripts_feedback": None,
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── Sidebar — pipeline status ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Pipeline Status")
    st.markdown("---")

    stage = st.session_state.stage
    steps = [
        ("input",     "📥 Requirements Input"),
        ("agent1",    "🧠 Agent 1 — Test Plan"),
        ("review1",   "👤 Review Gate 1"),
        ("agent2",    "📋 Agent 2 — Test Cases"),
        ("agent3",    "⚙️  Agent 3 — Scripts"),
        ("review2",   "👤 Review Gate 2"),
        ("complete",  "✅ Complete"),
    ]
    stage_order = [s[0] for s in steps]
    current_idx = stage_order.index(stage) if stage in stage_order else 0

    for i, (s_key, s_label) in enumerate(steps):
        if i < current_idx:
            st.success(s_label)
        elif i == current_idx:
            st.info(f"▶ {s_label}")
        else:
            st.markdown(f"⬜ {s_label}")

    st.markdown("---")
    if st.button("🔄 Reset Pipeline", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown(f"<small>Run ID: `{st.session_state.run_id}`</small>", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🤖 AI Test Intelligence Pipeline")
st.markdown("*Multi-agent workflow: Requirements → Test Plan → Test Cases → Automation Scripts*")
st.markdown("---")


# ─── STAGE: Input ─────────────────────────────────────────────────────────────
if st.session_state.stage == "input":
    st.markdown("## 📥 Step 1 — Provide Requirements")

    col1, col2 = st.columns([3, 1])
    with col1:
        input_method = st.radio("Input method", ["Paste text", "Upload file", "Use sample"], horizontal=True)

    requirements = ""
    if input_method == "Paste text":
        requirements = st.text_area(
            "Requirements",
            height=300,
            placeholder="Paste your feature requirements, user stories, or acceptance criteria here..."
        )
    elif input_method == "Upload file":
        uploaded = st.file_uploader("Upload a .txt or .md requirements file", type=["txt", "md"])
        if uploaded:
            requirements = uploaded.read().decode("utf-8")
            st.text_area("Preview", requirements, height=200, disabled=True)
    elif input_method == "Use sample":
        sample_path = Path("sample_inputs/requirements.txt")
        if sample_path.exists():
            requirements = sample_path.read_text()
            st.text_area("Sample Requirements (editable)", requirements, height=300, key="sample_edit")
            requirements = st.session_state.get("sample_edit", requirements)
        else:
            st.error("sample_inputs/requirements.txt not found.")

    st.markdown("### ⚙️ Optional: Repo Context")
    repo_context = st.text_area(
        "Paste your test repo structure / page object summary (optional — uses built-in default if empty)",
        height=120,
        placeholder="Describe your existing page objects, frameworks, and conventions..."
    )

    api_key = st.text_input("🔑 Anthropic API Key", type="password",
                             value=os.environ.get("ANTHROPIC_API_KEY", ""),
                             help="Your key is used only for this session and never stored.")

    if st.button("🚀 Start Pipeline", type="primary", use_container_width=True):
        if not requirements.strip():
            st.error("Please provide requirements before starting.")
        elif not api_key.strip():
            st.error("Please enter your Anthropic API key.")
        else:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            st.session_state.requirements = requirements
            st.session_state.repo_context = repo_context
            st.session_state.stage = "agent1"
            st.rerun()


# ─── STAGE: Agent 1 — generate test plan ──────────────────────────────────────
elif st.session_state.stage == "agent1":
    st.markdown("## 🧠 Agent 1 — Generating Test Plan")

    with st.spinner("Agent 1 is analysing requirements and building a test plan..."):
        try:
            from agents.agent1_test_plan import generate_test_plan_direct
            plan = generate_test_plan_direct(
                st.session_state.requirements,
                feedback=st.session_state.plan_feedback,
                revision=st.session_state.plan_revision,
            )
            st.session_state.test_plan = plan
            st.session_state.plan_revision += 1
            st.session_state.stage = "review1"
            st.rerun()
        except Exception as e:
            st.error(f"Agent 1 failed: {e}")
            st.session_state.stage = "input"


# ─── STAGE: Human Review Gate 1 ───────────────────────────────────────────────
elif st.session_state.stage == "review1":
    plan = st.session_state.test_plan

    st.markdown("## 👤 Human Review Gate 1 — Test Plan Approval")
    st.markdown(
        '<div class="review-banner">⚠️ QA Lead review required before proceeding. '
        'Approve the plan or reject with feedback to trigger a revision.</div>',
        unsafe_allow_html=True
    )

    # Display the plan
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"### 📋 {plan['title']}")
        st.markdown(f"**Scope:** {plan['scope']}")

        st.markdown("**Risk Areas:**")
        for r in plan["risk_areas"]:
            st.markdown(f"  - ⚠️ {r}")

        st.markdown("**Out of Scope:**")
        for o in plan["out_of_scope"]:
            st.markdown(f"  - ~~{o}~~")

        st.markdown("**Assumptions:**")
        for a in plan["assumptions"]:
            st.markdown(f"  - 💬 {a}")

    with col2:
        st.markdown("**Coverage Matrix:**")
        for item in plan["coverage_matrix"]:
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(item["priority"], "⚪")
            st.markdown(f"{priority_color} **{item['area']}**")
            st.markdown(f"  <small>{item['notes']}</small>", unsafe_allow_html=True)
            st.markdown("")

    with st.expander("📄 View raw JSON"):
        st.json(plan)

    st.markdown("---")
    st.markdown(f"**Revision #{st.session_state.plan_revision}**")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Approve — Proceed to Test Cases", type="primary", use_container_width=True):
            st.session_state.plan_feedback = None
            st.session_state.stage = "agent2"
            st.rerun()

    with col_b:
        with st.form("reject_form_1"):
            feedback = st.text_area("Rejection feedback (required)", placeholder="What needs to change?")
            if st.form_submit_button("❌ Reject — Send back to Agent 1", use_container_width=True):
                if feedback.strip():
                    st.session_state.plan_feedback = feedback
                    st.session_state.stage = "agent1"
                    st.rerun()
                else:
                    st.error("Please provide feedback before rejecting.")


# ─── STAGE: Agent 2 — generate test cases ─────────────────────────────────────
elif st.session_state.stage == "agent2":
    st.markdown("## 📋 Agent 2 — Generating Test Cases")

    with st.spinner("Agent 2 is generating and classifying test cases..."):
        try:
            from agents.agent2_test_cases import generate_test_cases_direct
            cases = generate_test_cases_direct(
                st.session_state.test_plan,
                st.session_state.requirements,
            )
            st.session_state.test_cases = cases
            st.session_state.automate_cases = [c for c in cases if c["classification"] == "automate"]
            st.session_state.manual_cases = [c for c in cases if c["classification"] in ("manual", "hybrid")]
            st.session_state.stage = "agent3" if st.session_state.automate_cases else "complete"
            st.rerun()
        except Exception as e:
            st.error(f"Agent 2 failed: {e}")


# ─── STAGE: Agent 3 — generate scripts ────────────────────────────────────────
elif st.session_state.stage == "agent3":
    st.markdown("## ⚙️ Agent 3 — Generating Automation Scripts")

    n = len(st.session_state.automate_cases)
    with st.spinner(f"Agent 3 is generating scripts for {n} automate-tagged cases..."):
        try:
            from agents.agent3_automation import generate_scripts_direct
            scripts = generate_scripts_direct(
                st.session_state.automate_cases,
                repo_context=st.session_state.get("repo_context") or None,
                feedback=st.session_state.scripts_feedback,
                revision=st.session_state.scripts_revision,
            )
            st.session_state.scripts = scripts
            st.session_state.scripts_revision += 1
            st.session_state.stage = "review2"
            st.rerun()
        except Exception as e:
            st.error(f"Agent 3 failed: {e}")


# ─── STAGE: Human Review Gate 2 ───────────────────────────────────────────────
elif st.session_state.stage == "review2":
    scripts = st.session_state.scripts
    cases = st.session_state.test_cases

    # Show test cases summary first
    st.markdown("## 📊 Test Case Summary")
    auto_c  = len(st.session_state.automate_cases)
    manual_c = len(st.session_state.manual_cases)
    total_c = len(cases)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="num">{total_c}</div><div class="lbl">Total Test Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="num">{auto_c}</div><div class="lbl">Automate</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="num">{manual_c}</div><div class="lbl">Manual / Hybrid</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Test cases table
    with st.expander("📋 View All Test Cases", expanded=False):
        filter_col = st.selectbox("Filter by classification", ["All", "automate", "manual", "hybrid"])
        display_cases = cases if filter_col == "All" else [c for c in cases if c["classification"] == filter_col]

        for tc in display_cases:
            cls = tc["classification"]
            pri = tc["priority"]
            badge_cls = f'badge-{cls}'
            badge_pri = f'badge-{pri}'
            st.markdown(
                f'**{tc["id"]}** — {tc["title"]} '
                f'<span class="badge {badge_cls}">{cls}</span> '
                f'<span class="badge {badge_pri}">{pri}</span>',
                unsafe_allow_html=True
            )
            st.markdown(f"*{tc['classification_reason']}*")
            with st.expander(f"Steps for {tc['id']}"):
                for step in tc["steps"]:
                    st.markdown(f"{step['step_number']}. **{step['action']}** → *{step['expected']}*")
                st.markdown(f"**Expected Result:** {tc['expected_result']}")
            st.markdown("---")

    # Scripts review
    st.markdown("## 👤 Human Review Gate 2 — Script Review")
    st.markdown(
        '<div class="review-banner">⚠️ Engineer review required. Check selector accuracy, '
        'pattern compliance, and page object usage before approving.</div>',
        unsafe_allow_html=True
    )
    st.markdown(f"**Revision #{st.session_state.scripts_revision}** — {len(scripts)} script file(s) generated")

    for script in scripts:
        with st.expander(f"📄 {script['file_path']}  [{script['test_case_id']}] — Zephyr: {script['zephyr_link']}"):
            st.markdown(f"**Framework:** {script['framework']}")
            st.markdown(f"**Page Objects:** {', '.join(script['page_objects_used'])}")
            st.code(script["script_content"], language="python")

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Approve — Finalise PR-Ready Output", type="primary", use_container_width=True):
            st.session_state.scripts_feedback = None
            st.session_state.stage = "complete"
            st.rerun()

    with col_b:
        with st.form("reject_form_2"):
            feedback = st.text_area("Rejection feedback (required)", placeholder="Selector issues, pattern violations, missing assertions?")
            if st.form_submit_button("❌ Reject — Send back to Agent 3", use_container_width=True):
                if feedback.strip():
                    st.session_state.scripts_feedback = feedback
                    st.session_state.stage = "agent3"
                    st.rerun()
                else:
                    st.error("Please provide feedback before rejecting.")


# ─── STAGE: Complete ──────────────────────────────────────────────────────────
elif st.session_state.stage == "complete":
    st.markdown("## ✅ Pipeline Complete!")
    st.success("All stages finished. Your PR-ready output is below.")

    cases = st.session_state.test_cases
    scripts = st.session_state.scripts
    plan = st.session_state.test_plan

    # Stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="num">{len(cases)}</div><div class="lbl">Test Cases</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="num">{len(st.session_state.automate_cases)}</div><div class="lbl">Automated</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="num">{len(st.session_state.manual_cases)}</div><div class="lbl">Manual</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-box"><div class="num">{len(scripts)}</div><div class="lbl">Script Files</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🗺️ Traceability Matrix")
    st.markdown("Requirements → Test Cases → Automation Scripts")

    # Build traceability table
    matrix_rows = []
    for tc in cases:
        script_match = next((s for s in scripts if s["test_case_id"] == tc["id"]), None)
        matrix_rows.append({
            "Test Case ID": tc["id"],
            "Title": tc["title"],
            "Classification": tc["classification"],
            "Priority": tc["priority"],
            "Script File": script_match["file_path"] if script_match else "—",
            "Zephyr Link": script_match["zephyr_link"] if script_match else "—",
        })

    import pandas as pd
    df = pd.DataFrame(matrix_rows)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📦 Downloads")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "📄 Test Plan (JSON)",
            json.dumps(plan, indent=2),
            file_name="test_plan.json",
            mime="application/json"
        )
    with col2:
        st.download_button(
            "📋 Test Cases (JSON)",
            json.dumps(cases, indent=2),
            file_name="test_cases.json",
            mime="application/json"
        )
    with col3:
        st.download_button(
            "⚙️ Scripts Manifest (JSON)",
            json.dumps(scripts, indent=2),
            file_name="automation_scripts.json",
            mime="application/json"
        )

    st.markdown("### 📄 Generated Script Files")
    for script in scripts:
        with st.expander(f"{script['file_path']}"):
            st.code(script["script_content"], language="python")
            st.download_button(
                f"Download {Path(script['file_path']).name}",
                script["script_content"],
                file_name=Path(script["file_path"]).name,
                key=f"dl_{script['test_case_id']}"
            )

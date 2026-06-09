"""
Agent 3 — Automation Script Generator

Ingests UI test repo context (page objects, helpers, selectors) and
generates Appium (Python) automation scripts that:
  - extend existing page objects
  - follow repo conventions
  - include Zephyr case linkage
  - are PR-ready

Supports revision loops when the engineer rejects a script batch.
"""
import json
import os
from pathlib import Path
import anthropic
from utils.models import PipelineState

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Default page object repo context (simulates ingesting a real repo)
DEFAULT_REPO_CONTEXT = """
# Mobile Test Repo — Page Object Structure

## Framework: Appium + pytest (Python)

## Directory Layout
tests/
  pages/
    base_page.py       # BasePage with find_element, wait_for, tap, type_text helpers
    login_page.py      # LoginPage(BasePage) — login flow
    home_page.py       # HomePage(BasePage) — post-login landing
    onboarding_page.py # OnboardingPage(BasePage) — new user carousel
  tests/
    test_login.py      # Existing login test examples
  conftest.py          # Appium driver setup, fixtures

## BasePage Helpers (base_page.py)
class BasePage:
    def find_element(self, locator: tuple) -> WebElement
    def tap(self, locator: tuple) -> None
    def type_text(self, locator: tuple, text: str) -> None
    def wait_for_visible(self, locator: tuple, timeout=10) -> WebElement
    def get_text(self, locator: tuple) -> str
    def is_displayed(self, locator: tuple) -> bool
    def swipe_up(self) -> None

## Selectors Convention
Locators are tuples: (MobileBy.ACCESSIBILITY_ID, "id_string")
Or: (MobileBy.ID, "com.myapp.android:id/element_id")

## conftest.py Driver Setup
@pytest.fixture(scope="session")
def driver():
    caps = { "platformName": "Android", "app": APP_PATH, ... }
    driver = webdriver.Remote("http://localhost:4723/wd/hub", caps)
    yield driver
    driver.quit()

## Existing Example (test_login.py)
def test_valid_login(driver):
    login_page = LoginPage(driver)
    login_page.enter_email("user@test.com")
    login_page.enter_password("Password123!")
    login_page.tap_login_button()
    home_page = HomePage(driver)
    assert home_page.is_displayed(home_page.WELCOME_BANNER)
"""

SYSTEM_PROMPT = """You are a senior mobile automation engineer.
Given test cases tagged for automation and the project's repo context, generate
production-quality Appium (Python + pytest) automation scripts.

ALWAYS respond with a valid JSON array (no markdown, no extra text):
[
  {
    "test_case_id": "TC-001",
    "test_case_title": "string",
    "framework": "Appium + pytest",
    "file_path": "tests/tests/test_<feature>.py",
    "script_content": "string — complete Python file content",
    "page_objects_used": ["LoginPage", "HomePage", ...],
    "zephyr_link": "ZEPHYR-TC-001"
  },
  ...
]

Rules:
1. Scripts must import from the page object structure described in the repo context
2. Use pytest fixtures (driver from conftest.py)
3. Add a docstring with: test case ID, title, and Zephyr link
4. Include parametrize where data-driven testing makes sense
5. Group related test cases into one file when they share a page object
6. Use descriptive assertion messages
7. Handle setup/teardown cleanly via pytest fixtures
"""


def run_agent3(state: PipelineState) -> PipelineState:
    """
    Node function for LangGraph. Generates (or revises) automation scripts.
    """
    automate_cases = state["automate_cases"]
    repo_context = state.get("repo_context") or DEFAULT_REPO_CONTEXT
    feedback = state.get("scripts_feedback")
    revision_count = state.get("scripts_revision_count", 0)

    if not automate_cases:
        print("[Agent 3] No automate-tagged cases — skipping.")
        return {**state, "current_stage": "complete"}

    feedback_block = ""
    if feedback and revision_count > 0:
        feedback_block = f"\nENGINEER REVIEW FEEDBACK (please address these issues):\n{feedback}\n"

    user_message = f"""REPO CONTEXT:
{repo_context}

TEST CASES TO AUTOMATE:
{json.dumps(automate_cases, indent=2)}
{feedback_block}
Generate automation scripts for all the test cases above.
Group logically related cases into the same test file.
"""

    print(f"\n{'='*60}")
    print(f"[Agent 3] Generating automation scripts (revision #{revision_count})...")
    print(f"  • {len(automate_cases)} cases to automate")
    print(f"{'='*60}")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    scripts = json.loads(raw)

    # Save scripts to disk
    scripts_dir = Path("outputs/scripts")
    scripts_dir.mkdir(parents=True, exist_ok=True)

    for script in scripts:
        # Derive a safe filename from the file_path
        fname = Path(script["file_path"]).name
        (scripts_dir / fname).write_text(script["script_content"], encoding="utf-8")

    # Save manifest
    (Path("outputs") / "automation_scripts.json").write_text(
        json.dumps(scripts, indent=2), encoding="utf-8"
    )

    print(f"[Agent 3] ✅ Generated {len(scripts)} script file(s):")
    for s in scripts:
        print(f"  • {s['file_path']}  [{s['test_case_id']}]")

    return {
        **state,
        "automation_scripts": scripts,
        "scripts_revision_count": revision_count + 1,
        "scripts_approved": None,
        "current_stage": "human_review_2",
    }


def generate_scripts_direct(automate_cases: list, repo_context: str = None,
                             feedback: str = None, revision: int = 0) -> list:
    """
    Standalone call used by Streamlit UI.
    Returns list of script dicts.
    """
    state: PipelineState = {
        "requirements_text": "",
        "repo_context": repo_context or DEFAULT_REPO_CONTEXT,
        "test_plan": None,
        "test_plan_revision_count": 1,
        "test_plan_feedback": None,
        "test_cases": automate_cases,
        "automate_cases": automate_cases,
        "manual_cases": [],
        "automation_scripts": None,
        "scripts_revision_count": revision,
        "scripts_feedback": feedback,
        "plan_approved": True,
        "scripts_approved": None,
        "current_stage": "agent3",
        "error_message": None,
        "run_id": "direct",
    }
    result = run_agent3(state)
    return result["automation_scripts"]

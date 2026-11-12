from bughound_agent import BugHoundAgent
from llm_client import MockClient

def test_workflow_runs_in_offline_mode_and_returns_shape():
    agent = BugHoundAgent(client=None)  # heuristic-only
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert isinstance(result, dict)
    assert "issues" in result
    assert "fixed_code" in result
    assert "risk" in result
    assert "logs" in result

    assert isinstance(result["issues"], list)
    assert isinstance(result["fixed_code"], str)
    assert isinstance(result["risk"], dict)
    assert isinstance(result["logs"], list)
    assert len(result["logs"]) > 0


def test_offline_mode_detects_print_issue():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])


def test_offline_mode_proposes_logging_fix_for_print():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    fixed = result["fixed_code"]
    assert "logging" in fixed
    assert "logging.info(" in fixed


def test_mock_client_forces_llm_fallback_to_heuristics_for_analysis():
    # MockClient returns non-JSON for analyzer prompts, so agent should fall back.
    agent = BugHoundAgent(client=MockClient())
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])
    # Ensure we logged the fallback path
    assert any("Falling back to heuristics" in entry.get("message", "") for entry in result["logs"])
    
def test_analyzer_rejects_incomplete_ai_output():
    agent = BugHoundAgent()

    # Valid JSON, but missing required severity and msg fields
    malformed_output = '[{"type": "Reliability"}]'

    result = agent._parse_json_array_of_issues(malformed_output)

    # The guardrail should reject incomplete AI output
    assert result is None
    
def test_comments_only_input_is_not_autofixed():
    agent = BugHoundAgent(client=None)

    code = """
# This is only a comment
# TODO: implement this later
"""

    result = agent.run(code)

    assert result["issues"] == []
    assert result["fixed_code"] == code
    assert result["risk"]["level"] == "high"
    assert result["risk"]["should_autofix"] is False
    assert any(
        "No executable code" in log["message"]
        for log in result["logs"]
    )
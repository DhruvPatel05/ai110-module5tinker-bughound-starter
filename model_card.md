# BugHound Model Card

## System Overview

**Name:** BugHound

**Purpose:**  
BugHound is an experimental AI-powered debugging assistant that analyzes Python code, identifies potential issues, proposes fixes, evaluates the risk of those fixes, and decides whether a change is safe enough to auto-apply or should be reviewed by a human.

**Intended Users:**  
Developers and students who want assistance identifying common code quality, reliability, and maintainability problems while keeping a human involved when a proposed change may be unsafe.

---

## Workflow

BugHound follows an agent loop:

**PLAN → ANALYZE → ACT → TEST → REFLECT**

- **PLAN:** Prepares the code-analysis and fix workflow.
- **ANALYZE:** Detects potential issues using either heuristics or Gemini.
- **ACT:** Proposes a fix using a heuristic fixer or Gemini.
- **TEST:** Uses the risk assessor to evaluate the proposed change.
- **REFLECT:** Decides whether the fix can be auto-applied or requires human review.

In heuristic/offline mode, BugHound uses predefined rules and does not require API calls. In Gemini mode, the agent attempts to use the LLM for analysis and fixing. If the AI output is invalid, incomplete, unavailable, or cannot be parsed, BugHound can fall back to heuristics.

---

## Inputs and Outputs

I tested BugHound with different types of Python input, including:

- `sample_code/mixed_issues.py`
- Cleaner code intended to require few or no changes
- Empty or comments-only input
- Code containing `print()`, `TODO`, and a bare `except:`

For `mixed_issues.py`, the heuristic analyzer detected three issues:

1. A low-severity code quality issue for using `print()`.
2. A high-severity reliability issue for using a bare `except:`.
3. A medium-severity maintainability issue for a `TODO` comment.

BugHound produced a proposed fix, a unified diff, a risk score and level, an auto-fix decision, and an agent trace explaining the workflow decisions.

---

## Reliability Rules

### Issue Severity Scoring

The risk assessor decreases the score based on issue severity. High-severity issues receive a larger penalty than medium- or low-severity issues.

**Benefit:** This makes BugHound more cautious when serious reliability problems are detected.

**Possible false positive:** A high-severity label from an imperfect analyzer could make a harmless change appear more dangerous than it actually is.

**Possible false negative:** An incorrectly labeled low-severity issue could receive too small a penalty even when the proposed fix changes important behavior.

### Structural Change Checks

BugHound checks for potentially dangerous structural changes, including removed return statements, significantly shortened code, and modifications to bare exception handling.

**Benefit:** These rules can detect fixes that may unexpectedly alter program behavior.

**Possible false positive:** A legitimate refactor could shorten the program substantially without making it unsafe.

**Possible false negative:** A fix could preserve the number of lines and return statements while still changing control flow or program behavior in an unsafe way.

### Stricter Auto-Fix Threshold

I changed the auto-fix policy so that a fix must be classified as low risk **and have a score of at least 90** before BugHound can auto-fix it.

A score from 75–89 can still be considered low risk, but it now requires human review.

This makes the agent more conservative about acting autonomously.

---

## Failure Modes

### 1. Invalid AI Output

During a Gemini run, the analyzer returned output that BugHound could not parse as the expected JSON structure. BugHound rejected the response and fell back to the heuristic analyzer.

I strengthened this behavior by requiring AI-generated issues to contain valid `type`, `severity`, and `msg` fields. Severity must also be `Low`, `Medium`, or `High`.

This prevents incomplete but syntactically valid AI output from silently moving through the workflow.

### 2. Empty AI Fix

During a Gemini run, the LLM fixer returned empty output. BugHound detected the failure and fell back to its heuristic fixer rather than treating the empty response as a valid fix.

### 3. Comments-Only False Positive

The heuristic analyzer searches for `TODO`, so a comments-only file containing a TODO could be treated as code requiring analysis even though there is no executable code.

I added a guardrail that detects empty or comments-only input. BugHound now avoids analyzing or modifying that input, assigns high risk, disables auto-fix, and recommends human review.

A reliability test protects this behavior.

---

## Heuristic vs. Gemini

Heuristic mode was predictable and deterministic. It consistently identified predefined patterns such as `print()`, `TODO`, and bare `except:` statements.

Gemini mode was more flexible but less predictable. In my testing, Gemini produced analyzer output that could not be parsed as the required JSON structure, and the fixer also returned empty output during one run.

The fallback behavior was therefore important. When Gemini output could not be trusted, BugHound used deterministic heuristics instead of continuing with malformed AI output.

This demonstrates that the LLM is one tool inside the agent workflow rather than the sole decision-maker.

---

## Human-in-the-Loop

BugHound should refuse to automatically apply a fix when its confidence is insufficient or when the proposed change could affect program behavior.

One trigger I implemented is the stricter auto-fix threshold:

**Trigger:** Risk score is below 90.

**Implementation location:** `reliability/risk_assessor.py`

**Behavior:** Set `should_autofix` to `False` even if the overall risk level is classified as low.

**Message to user:**  
“Fix is not safe enough to auto-apply. Human review recommended.”

I also added a guardrail for empty or comments-only input so BugHound does not confidently modify input that contains no executable code.

---

## One Future Improvement

A useful low-complexity improvement would be to validate that proposed Python fixes are syntactically valid before allowing auto-fix.

BugHound could use Python's built-in `ast.parse()` on the proposed code during the TEST stage. If parsing fails, the risk level should increase and `should_autofix` should automatically become `False`.

This would add a deterministic reliability check without requiring another API request and would prevent BugHound from automatically applying malformed Python generated by an LLM.

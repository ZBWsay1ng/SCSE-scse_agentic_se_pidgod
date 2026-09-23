# SCSE Agentic Software Engineering — Group 2

This project continues Requirements Engineering with the Plan and Develop stage.
It uses the local Ollama model `qwen3:8b` to produce validated artifacts.

```text
brief.txt -> Analyst -> artifacts/requirements.json
                     -> Planner -> artifacts/plan.json
                                -> Developer -> navigation_logic.py
```

Each model request starts a new conversation. Planner receives only the validated
requirements artifact as project context; Developer receives only the validated
plan. Earlier agents' conversations are not forwarded.

## Prerequisites and execution

- Python 3.10 or later. The Python scripts use only the standard library.
- Ollama running locally at `http://127.0.0.1:11434` with `qwen3:8b` installed.
- If needed, run `ollama pull qwen3:8b` once, then start `ollama serve` in a
  separate terminal (unnecessary when the Ollama desktop service is running).

In PowerShell:

```powershell
Set-Location 'E:\SCSE\guoup-project\Plan and Develop\scse_agentic_se_2'

# Continue from the included requirements artifact from the first exercise:
python run_planner.py
python run_developer.py

# Offline verification; Ollama is not needed:
python -m unittest -v
```

To regenerate from the original brief, run `python run_analyst.py` before the
Planner and Developer. Rerun all downstream stages after changing an upstream
artifact. The scripts resolve artifact paths relative to their own location.
They validate outputs before writing; failed validation leaves any previous
artifact in place. An old artifact is not evidence that the latest run succeeded.

## Files

| File | Purpose |
| --- | --- |
| `brief.txt` | Original robot navigation brief |
| `analyst_agent.py`, `run_analyst.py` | First-stage requirements extraction and validation |
| `brief_to_req.py`, `robot_requirements.txt` | Original free-text requirements experiment; not consumed by the pipeline |
| `llm_client.py` | Shared local Qwen transport, isolated messages, JSON mode where applicable |
| `planner_agent.py`, `run_planner.py` | Generate, validate and save the navigation plan |
| `developer_agent.py`, `run_developer.py` | Generate, validate and save Python navigation code |
| `artifacts/requirements.json` | Preserved first-exercise structured requirements |
| `artifacts/plan.json` | Qwen-generated navigation plan |
| `navigation_logic.py` | Qwen-generated pure navigation function |
| `test_navigation.py` | Offline behavioral and validation regression tests |

The original Requirements Engineering folder and the teacher's template are
unchanged. In this copy, the Analyst uses the shared transport and its validation
requires a nonempty goal and both safety flags to be exactly `true`.

## Navigation contract and planning choices

```python
decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None)
```

- The three obstacle inputs must be actual booleans. `True` means blocked.
- Goal values are `"ahead"`, `"left"`, `"right"`, or `None` (unknown).
- Invalid inputs raise `ValueError` before a navigation decision is made.
- Stop if all three paths are blocked.
- Otherwise take the goal direction if it is known and safe.
- Otherwise choose the first safe direction in the plan's `fallback_order`.
  The Planner is instructed to use `FORWARD`, then `LEFT`, then `RIGHT`.
- Return only `FORWARD`, `LEFT`, `RIGHT`, or `STOP`.

The fallback ordering and invalid-input policy are explicit design choices made
for this exercise; the original brief did not specify them. LEFT/RIGHT represent
discrete navigation commands toward those sensed directions. Physical turning,
actuation, goal-arrival detection, path memory and simulator integration are not
implemented. This is a local reactive decision component, not a complete path
planner or a guarantee of eventual goal arrival.

Example after generation (no model call at runtime):

```python
from navigation_logic import decide_action

assert decide_action(False, False, True, "left") == "LEFT"
assert decide_action(False, False, True, "right") == "FORWARD"
assert decide_action(True, True, True) == "STOP"
```

## Validation

Requirements and plans have strict schemas. Ordered plan identifiers encode stop,
goal preference and fallback behavior; the natural-language strategy is explanatory.
Developer output must contain exactly the expected function and pass a restricted
AST check before its behavior is evaluated. This validator supports a small pure
Python subset, not arbitrary Python programs. No imports, I/O, loops, attributes,
recursion or top-level executable statements are accepted. Up to three Developer
attempts are allowed, using only the plan and validation feedback.

Every generated function is checked against all 32 combinations of obstacle state
and goal, 8 omitted-goal calls, and 32 invalid-input cases. Offline tests also check
safety independently of fallback order, artifact validation, rejection of unsafe
code, isolation of stage contexts, and failed-generation retries.

The included requirements artifact is reused from the first exercise. The included
plan and navigation source are generated by the local Qwen model, then validated;
they are not manually substituted outputs. Generation may vary on later runs.

## Submission

The course instructions require a GitHub repository named `scse_agentic_se_2`
containing the project files, with its link submitted to Moodle. This folder is
the local deliverable; creating/pushing a remote repository and submitting to
Moodle are separate actions.

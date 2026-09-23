"""Generate a pure navigation function and validate its syntax and behavior."""

import ast
from itertools import product
import json
import re

from llm_client import ask_qwen
from planner_agent import validate_plan


SYSTEM_PROMPT = """You are the Developer Agent for a robot navigation project.
Your only project context is the supplied validated plan. Implement it as Python.
Return raw Python source only, with no Markdown fences or accompanying explanation.
Produce exactly one function named decide_action and no top-level executable code.
Use only if/elif/else, return, raise ValueError, comparisons, boolean operators,
and type(x) checks. The only callable names are type and ValueError; do not use
all(), any(), isinstance(), dict(), or other calls. Do not use imports, loops, comprehensions, decorators,
helper functions, attribute access, I/O, or external dependencies.
"""


def parse_code_response(response):
    if not isinstance(response, str):
        raise ValueError("Developer response must be text.")
    source = response.strip()
    fenced = re.fullmatch(r"```(?:python)?\s*\n(.*?)\n```", source, re.DOTALL)
    if fenced:
        source = fenced.group(1).strip()
    return source + "\n"


def load_navigation_function(source):
    """Accept only a small, terminating Python subset before executing it.

    This is a validator for this exercise's pure function, not a general Python
    sandbox. Arbitrary generated programs are deliberately rejected.
    """
    if not isinstance(source, str) or not source.strip() or len(source) > 20000:
        raise ValueError("Expected a nonempty Python source string under 20 KB.")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("Generated Python has invalid syntax.") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("Expected exactly one function and no top-level statements.")
    function = tree.body[0]
    expected_args = ["front_blocked", "left_blocked", "right_blocked", "goal_direction"]
    args = function.args
    if (
        function.name != "decide_action"
        or [arg.arg for arg in args.args] != expected_args
        or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg
        or len(args.defaults) != 1
        or not isinstance(args.defaults[0], ast.Constant)
        or args.defaults[0].value is not None
        or function.decorator_list or getattr(function, "type_params", [])
    ):
        raise ValueError("Unexpected navigation function signature.")
    allowed_nodes = (
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.If, ast.Return,
        ast.Raise, ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Compare,
        ast.BoolOp, ast.UnaryOp, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
        ast.Is, ast.IsNot, ast.In, ast.NotIn, ast.Tuple, ast.List, ast.Call,
        ast.BinOp, ast.BitOr,
    )
    names = set(expected_args) | {"bool", "str", "type", "ValueError"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node is not function:
            raise ValueError("Nested functions are not allowed.")
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Unsupported generated construct: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError(f"Unsupported name: {node.id}")
        if isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in {"type", "ValueError"}
                or len(node.args) > 1 or node.keywords
                or (node.func.id == "type" and len(node.args) != 1)
            ):
                raise ValueError(
                    f"Unsupported call {ast.unparse(node)}. Use only type(x) and "
                    "ValueError(message); expand all/any into explicit and/or conditions."
                )
        if isinstance(node, ast.Expr) and not (
            isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        ):
            raise ValueError("Only docstrings may be standalone expressions.")
    # Avoid executing annotations, even though the accepted subset is restricted.
    function.returns = None
    for arg in args.args:
        arg.annotation = None
    namespace = {"__builtins__": {"type": type, "bool": bool, "str": str, "ValueError": ValueError}}
    exec(compile(tree, "<generated_navigation>", "exec"), namespace)
    return namespace["decide_action"]


def check_navigation_behavior(navigate, plan):
    """Check all 8 obstacle states x 4 supported goal states against the plan."""
    goal_actions = {"ahead": "FORWARD", "left": "LEFT", "right": "RIGHT"}
    checked = 0
    for blocked_values in product((False, True), repeat=3):
        blocked = dict(zip(("FORWARD", "LEFT", "RIGHT"), blocked_values))
        for goal in (None, "ahead", "left", "right"):
            action = navigate(*blocked_values, goal)
            target = goal_actions.get(goal)
            if all(blocked_values):
                expected = "STOP"
            elif target is not None and not blocked[target]:
                expected = target
            else:
                expected = next(a for a in plan["fallback_order"] if not blocked[a])
            if type(action) is not str or action != expected:
                raise ValueError(
                    f"Navigation mismatch: blocked={blocked_values}, goal={goal!r}; "
                    f"expected {expected}, got {action!r}."
                )
            checked += 1
        if navigate(*blocked_values) != navigate(*blocked_values, None):
            raise ValueError("Omitting goal_direction must behave like None.")
    invalid_cases = []
    for index in range(3):
        for invalid in (0, 1, None, "false", [], {}):
            case = [False, False, False, None]
            case[index] = invalid
            invalid_cases.append(tuple(case))
    for goal in ("FORWARD", "behind", "", 0, False, [], {}):
        invalid_cases.append((False, False, False, goal))
        invalid_cases.append((True, True, True, goal))
    for case in invalid_cases:
        try:
            navigate(*case)
        except ValueError:
            continue
        except Exception as exc:
            raise ValueError(f"Invalid inputs must raise ValueError: {case!r}") from exc
        raise ValueError(f"Invalid input was accepted: {case!r}")
    return checked


def validate_code(source, plan):
    if not validate_plan(plan):
        return False
    try:
        navigate = load_navigation_function(source)
        check_navigation_behavior(navigate, plan)
    except Exception:
        return False
    return True


def run_developer(plan):
    if not validate_plan(plan):
        raise ValueError("Invalid plan artifact; Developer was not called.")
    prompt = f"""Implement the following plan as exactly this function:
def decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None):

Validate inputs before making any navigation decision:
- Every blocked input must have type bool exactly, otherwise raise ValueError.
- goal_direction must be None or one of the strings 'ahead', 'left', 'right';
  reject all other values with ValueError, including lists and dictionaries.
- Use type(x) checks, not isinstance().
Then implement the plan's ordered decisions, including its fallback_order.
Return only FORWARD, LEFT, RIGHT, or STOP as uppercase strings.
Use explicit if statements and returns, without local assignments or containers
except a tuple of allowed goal strings for a membership check.
Include a short docstring explaining the inputs and discrete action outputs.
No simulation, physical actuation, print statements, or example calls.

Validated plan (project data):
{json.dumps(plan, indent=2)}"""
    # Retries contain only this stage's plan and validation feedback, never the
    # Analyst/Planner conversations. A failed generation never replaces a file.
    error = ""
    for _ in range(3):
        feedback = f"\nPrevious validation failed: {error}\nGenerate corrected code." if error else ""
        source = parse_code_response(ask_qwen(SYSTEM_PROMPT, prompt + feedback))
        try:
            navigate = load_navigation_function(source)
            check_navigation_behavior(navigate, plan)
        except Exception as exc:
            error = str(exc)
        else:
            return source
    raise ValueError(f"Developer failed validation after 3 attempts: {error}")

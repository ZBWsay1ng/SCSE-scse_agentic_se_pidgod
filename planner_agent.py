"""Turn a validated requirements artifact into an explicit navigation plan."""

import json

from analyst_agent import parse_json_response, validate_requirements
from llm_client import ask_qwen


ACTIONS = ["FORWARD", "LEFT", "RIGHT", "STOP"]
DECISIONS = ["stop_if_all_blocked", "prefer_safe_goal", "first_safe_fallback"]
INTERFACE = {
    "function_name": "decide_action",
    "parameters": [
        "front_blocked", "left_blocked", "right_blocked", "goal_direction"
    ],
    "goal_values": ["ahead", "left", "right", None],
    "invalid_input": "raise ValueError",
}

SYSTEM_PROMPT = """You are the Planner Agent for a robot navigation project.
Decide how the software should behave using only the supplied requirements artifact.
Return one JSON object, without Markdown or explanations outside JSON.
Preserve the goal and safety requirements. Never plan movement into a blocked path.
Use deterministic, ordered decisions. Your plan will be the Developer's sole
project context. Do not generate Python code or invent sensors or environments.
"""


def validate_plan(data):
    if not isinstance(data, dict):
        return False
    if set(data) != {
        "goal", "strategy", "allowed_actions", "decisions", "fallback_order",
        "stop_condition", "interface",
    }:
        return False
    for key in ("goal", "strategy"):
        if not isinstance(data[key], str) or not data[key].strip():
            return False
    if data["allowed_actions"] != ACTIONS or data["decisions"] != DECISIONS:
        return False
    order = data["fallback_order"]
    if not isinstance(order, list) or len(order) != 3:
        return False
    if not all(isinstance(action, str) for action in order):
        return False
    if set(order) != set(ACTIONS[:3]):
        return False
    return (
        data["stop_condition"] == "all_directions_blocked"
        and data["interface"] == INTERFACE
    )


def run_planner(requirement):
    if not validate_requirements(requirement):
        raise ValueError("Invalid requirements artifact; Planner was not called.")
    schema = {
        "goal": requirement["goal"],
        "strategy": "Describe safe goal-first navigation and the fallback order.",
        "allowed_actions": ACTIONS,
        "decisions": DECISIONS,
        "fallback_order": ["FORWARD", "LEFT", "RIGHT"],
        "stop_condition": "all_directions_blocked",
        "interface": INTERFACE,
    }
    prompt = f"""Create a navigation plan with exactly this JSON structure:
{json.dumps(schema, indent=2)}

Keep the goal exactly as in the requirements. Write your own strategy description.
Use the listed decision identifiers in exactly this priority order:
1. STOP when all three directions are blocked.
2. If the optional goal direction is known and unblocked, choose that direction.
3. Otherwise choose the first unblocked direction in fallback_order.
Use FORWARD, LEFT, RIGHT as the deterministic fallback order.
Keep all other fields as specified. True means blocked; False means safe.
Goal 'ahead' maps to FORWARD, 'left' to LEFT, and 'right' to RIGHT.
None means no goal information. Invalid inputs must raise ValueError.
LEFT/RIGHT are discrete commands toward the corresponding sensed direction;
physical turning and simulator integration are outside this component.

Validated requirements (project data):
{json.dumps(requirement, indent=2)}"""
    response = ask_qwen(SYSTEM_PROMPT, prompt, json_output=True)
    plan = parse_json_response(response)
    if not validate_plan(plan):
        raise ValueError("Qwen did not return a valid navigation plan.")
    if plan["goal"] != requirement["goal"]:
        raise ValueError("The plan changed the requirements goal.")
    return plan

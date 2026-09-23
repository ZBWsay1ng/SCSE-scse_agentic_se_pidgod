import json
import re
from llm_client import MODEL_NAME, ask_qwen


def parse_json_response(response_text):
    if not isinstance(response_text, str):
        return None
    response_text = response_text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)

        if match is None:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def validate_requirements(result):
    required_keys = {
        "goal",
        "allowed_actions",
        "safe_stop",
        "avoid_obstacles"
    }

    if not isinstance(result, dict):
        return False

    if set(result.keys()) != required_keys:
        return False

    if not isinstance(result["goal"], str) or not result["goal"].strip():
        return False

    if result["allowed_actions"] != ["FORWARD", "LEFT", "RIGHT", "STOP"]:
        return False

    if result["safe_stop"] is not True:
        return False

    if result["avoid_obstacles"] is not True:
        return False

    return True


def run_analyst(brief_text):
    system_prompt = """You are an analyst agent for a software engineering project.
Your only responsibility is to convert a human project brief into explicit software requirements.
You must return valid JSON only.
Do not explain your answer.
Do not use markdown.
Do not add any extra keys.
The allowed robot navigation actions must be only FORWARD, LEFT, RIGHT, and STOP."""

    user_prompt = f"""Convert the following robot navigation brief into this exact JSON structure:

{{
    "goal": "string",
    "allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
    "safe_stop": true,
    "avoid_obstacles": true
}}

Rules:
- The "goal" value must describe the navigation objective from the brief.
- The "allowed_actions" value must be exactly ["FORWARD", "LEFT", "RIGHT", "STOP"].
- The "safe_stop" value must be true if the robot should stop when no safe path exists.
- The "avoid_obstacles" value must be true if the robot must avoid blocked directions.
- Return only the JSON object.

Brief:
{brief_text}"""

    response_text = ask_qwen(system_prompt, user_prompt, json_output=True)
    requirements = parse_json_response(response_text)

    if not validate_requirements(requirements):
        raise ValueError("Qwen did not return valid requirements JSON.")

    return requirements

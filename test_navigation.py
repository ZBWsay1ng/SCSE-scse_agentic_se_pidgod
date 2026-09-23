"""Offline regression tests; these never call Ollama."""

from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from analyst_agent import validate_requirements
from developer_agent import (
    check_navigation_behavior, load_navigation_function, run_developer, validate_code,
)
from planner_agent import run_planner, validate_plan


BASE_DIR = Path(__file__).resolve().parent


class NavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((BASE_DIR / "artifacts" / "plan.json").read_text(encoding="utf-8"))
        cls.requirements = json.loads(
            (BASE_DIR / "artifacts" / "requirements.json").read_text(encoding="utf-8")
        )
        cls.source = (BASE_DIR / "navigation_logic.py").read_text(encoding="utf-8")
        cls.navigate = staticmethod(load_navigation_function(cls.source))

    def test_complete_decision_table_and_invalid_inputs(self):
        self.assertEqual(check_navigation_behavior(self.navigate, self.plan), 32)

    def test_safety_and_goal_priority_independent_of_fallback(self):
        directions = ("FORWARD", "LEFT", "RIGHT")
        goals = {"ahead": "FORWARD", "left": "LEFT", "right": "RIGHT"}
        for state in product((False, True), repeat=3):
            blocked = dict(zip(directions, state))
            for goal in (None, *goals):
                with self.subTest(blocked=state, goal=goal):
                    action = self.navigate(*state, goal)
                    self.assertIn(action, [*directions, "STOP"])
                    self.assertEqual(action == "STOP", all(state))
                    if action != "STOP":
                        self.assertFalse(blocked[action])
                    if goal is not None and not blocked[goals[goal]]:
                        self.assertEqual(action, goals[goal])

    def test_artifacts_and_generated_code_are_valid(self):
        self.assertTrue(validate_requirements(self.requirements))
        self.assertTrue(validate_plan(self.plan))
        self.assertEqual(self.plan["goal"], self.requirements["goal"])
        self.assertTrue(validate_code(self.source, self.plan))

    def test_requirements_reject_disabled_safety_and_bad_schema(self):
        for field in ("safe_stop", "avoid_obstacles"):
            for value in (False, 1, "true"):
                broken = deepcopy(self.requirements)
                broken[field] = value
                self.assertFalse(validate_requirements(broken))
        for value in (None, [], {}, {**self.requirements, "extra": True}):
            self.assertFalse(validate_requirements(value))

    def test_plan_rejects_unsafe_or_ambiguous_rules(self):
        cases = {
            "fallback_order": [["FORWARD", "FORWARD", "RIGHT"], [[], "LEFT", "RIGHT"]],
            "decisions": [list(reversed(self.plan["decisions"]))],
            "stop_condition": ["never"],
            "allowed_actions": [["BACKWARD", "STOP"]],
            "interface": [{}],
            "strategy": [""],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    broken = deepcopy(self.plan)
                    broken[field] = value
                    self.assertFalse(validate_plan(broken))

    def test_code_validator_rejects_syntax_side_effects_and_unsafe_behavior(self):
        samples = [
            "this is not valid Python!",
            "import os\n" + self.source,
            self.source + "\nprint('unexpected top-level execution')\n",
            "def decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None):\n"
            "    return 'FORWARD'\n",
            "def decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None):\n"
            "    while True:\n        pass\n",
            "def decide_action(front_blocked, left_blocked, right_blocked, goal_direction=None):\n"
            "    return open('unexpected.txt', 'w')\n",
        ]
        for source in samples:
            with self.subTest(source=source[:60]):
                self.assertFalse(validate_code(source, self.plan))

    def test_invalid_artifacts_never_reach_model(self):
        with patch("planner_agent.ask_qwen") as model:
            with self.assertRaises(ValueError):
                run_planner({})
            model.assert_not_called()
        with patch("developer_agent.ask_qwen") as model:
            with self.assertRaises(ValueError):
                run_developer({})
            model.assert_not_called()

    def test_context_isolation(self):
        with patch("planner_agent.ask_qwen", return_value=json.dumps(self.plan)) as model:
            run_planner(self.requirements)
            self.assertIn(json.dumps(self.requirements, indent=2), model.call_args.args[1])
            self.assertNotIn("ROBOT NAVIGATION BRIEF", model.call_args.args[1])
        with patch("developer_agent.ask_qwen", return_value=self.source) as model:
            run_developer(self.plan)
            self.assertIn(json.dumps(self.plan, indent=2), model.call_args.args[1])
            self.assertNotIn("ROBOT NAVIGATION BRIEF", model.call_args.args[1])

    def test_developer_retries_invalid_generation(self):
        with patch("developer_agent.ask_qwen", side_effect=["invalid code!", self.source]) as model:
            self.assertEqual(run_developer(self.plan), self.source)
            self.assertEqual(model.call_count, 2)
        with patch("developer_agent.ask_qwen", return_value="invalid code!") as model:
            with self.assertRaises(ValueError):
                run_developer(self.plan)
            self.assertEqual(model.call_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)

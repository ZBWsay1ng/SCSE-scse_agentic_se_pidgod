"""Read requirements.json and save only a validated plan.json."""

import json
from pathlib import Path

from planner_agent import run_planner


def main():
    base_dir = Path(__file__).resolve().parent
    artifacts = base_dir / "artifacts"
    requirements = json.loads((artifacts / "requirements.json").read_text(encoding="utf-8"))
    plan = run_planner(requirements)
    output = artifacts / "plan.json"
    output.write_text(json.dumps(plan, indent=4) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=4))
    print(f"Saved validated plan to {output}")


if __name__ == "__main__":
    main()

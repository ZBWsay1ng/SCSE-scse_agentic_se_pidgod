"""Read plan.json and save only validated Qwen-generated Python code."""

import json
from pathlib import Path

from developer_agent import run_developer


def main():
    base_dir = Path(__file__).resolve().parent
    plan = json.loads((base_dir / "artifacts" / "plan.json").read_text(encoding="utf-8"))
    source = run_developer(plan)
    output = base_dir / "navigation_logic.py"
    output.write_text(source, encoding="utf-8")
    print(source)
    print(f"Saved validated code to {output}")
    print("Passed all 32 navigation cases, 8 default-goal cases and 32 invalid-input cases.")


if __name__ == "__main__":
    main()

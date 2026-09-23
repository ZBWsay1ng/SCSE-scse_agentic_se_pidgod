import json
import os
import urllib.request


MODEL_NAME = "qwen3:8b"


def ask_qwen(system_prompt, user_prompt):
    data = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "stream": False
    }

    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["message"]["content"]


def main():
    base_dir = os.path.dirname(__file__)
    brief_path = os.path.join(base_dir, "brief.txt")
    output_path = os.path.join(base_dir, "robot_requirements.txt")

    with open(brief_path, "r", encoding="utf-8") as file:
        brief_text = file.read()

    system_prompt = """You are a software requirements analyst.
Your task is to read a human-written project brief and turn it into clear software requirements."""

    user_prompt = f"""Read the brief below and write the software requirements in a clear list.

Brief:
{brief_text}"""

    requirements_text = ask_qwen(system_prompt, user_prompt)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(requirements_text)

    print(requirements_text)
    print()
    print("Saved to robot_requirements.txt")


if __name__ == "__main__":
    main()

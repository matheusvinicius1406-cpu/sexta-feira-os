"""Fix SUBAGENT_ALLOWED_TOOLS in .env and .env.template.
Pydantic expects JSON array format for list[str] fields."""
import re

FILES = [".env", ".env.template"]
CORRECT_LINE = 'SUBAGENT_ALLOWED_TOOLS=["recall","list_capabilities","call_api"]'

for filepath in FILES:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"{filepath}: not found, skipping")
        continue

    lines = content.split("\n")
    new_lines = []
    replaced = False
    for line in lines:
        if re.search(r"subagent_allowed_tools", line, re.IGNORECASE):
            new_lines.append(CORRECT_LINE)
            replaced = True
            print(f"{filepath}: replaced line")
        else:
            new_lines.append(line)

    if not replaced:
        # Add after SUBAGENTS_ENABLED line
        new_lines.append(CORRECT_LINE)
        print(f"{filepath}: added line")

    content = "\n".join(new_lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    # Verify
    with open(filepath, "r") as f:
        for line in f:
            if "SUBAGENT_ALLOWED" in line:
                stripped = line.strip()
                print(f"  VERIFIED: {stripped}")
                import json
                val = stripped.split("=", 1)[1]
                json.loads(val)  # will raise if invalid
                print(f"  Valid JSON OK")

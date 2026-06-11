#!/usr/bin/env python3
"""PreToolUse hook: block Edit/Write tool calls that target .env files."""
import json
import os
import sys

try:
    data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

path = (data.get("tool_input") or {}).get("file_path", "")
name = os.path.basename(path)
if name == ".env" or name.startswith(".env."):
    print("BLOCKED: .env file edits not allowed", file=sys.stderr)
    sys.exit(2)

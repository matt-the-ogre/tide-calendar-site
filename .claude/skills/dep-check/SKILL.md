---
name: dep-check
description: Check Python dependency compatibility with Dockerfile base image. Run before committing requirements.txt changes.
---

# Dependency Compatibility Check

Verify all pinned Python packages in `requirements.txt` are compatible with the Dockerfile's Python version.

## Steps

1. Parse the Python version from the Dockerfile `FROM` line:
   ```bash
   grep '^FROM python:' Dockerfile | sed 's/FROM python:\([0-9.]*\).*/\1/'
   ```

2. For each pinned package in `requirements.txt` (lines matching `pkg==version`):
   ```bash
   curl -s "https://pypi.org/pypi/${PKG}/${VERSION}/json" | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['requires_python'])"
   ```

3. Compare each package's `requires_python` against the Dockerfile Python version. Flag any incompatibilities.

4. Output a summary table:
   ```
   | Package | Version | Requires Python | Dockerfile Python | Status |
   ```

5. If any incompatibilities found, warn clearly and suggest either:
   - Downgrading the package to a compatible version
   - Bumping the Dockerfile base image

## When to Run
- Before committing changes to `requirements.txt`
- When Dependabot suggests dependency bumps
- After running `pip install --upgrade`

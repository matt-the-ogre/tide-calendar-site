#!/usr/bin/env python3
"""
Generate version information file at build time.
This script is run during Docker build to capture build metadata.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone

def get_git_commit_hash():
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'unknown'

def get_git_branch():
    """Get the current git branch."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'unknown'

def get_version():
    """Get version from package.json or default to 1.0.0."""
    try:
        import os
        package_json_path = os.path.join(os.path.dirname(__file__), '..', 'package.json')
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                import json
                package_data = json.load(f)
                return package_data.get('version', '1.0.0')
    except Exception:
        pass
    return '1.0.0'

def main():
    """Generate version info JSON file."""
    version_info = {
        'version': get_version(),
        'commit_hash': get_git_commit_hash(),
        'branch': get_git_branch(),
        'build_timestamp': datetime.now(timezone.utc).isoformat(),
    }

    # Write to version_info.json in the same directory as this script
    output_path = os.path.join(os.path.dirname(__file__), 'version_info.json')
    with open(output_path, 'w') as f:
        json.dump(version_info, f, indent=2)

    print(f"Generated version info: {json.dumps(version_info, indent=2)}")
    return 0

if __name__ == '__main__':
    import os
    sys.exit(main())

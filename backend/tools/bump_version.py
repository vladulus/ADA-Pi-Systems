#!/usr/bin/env python3
"""
Version bumping tool:
 - Increases version or build number
 - Updates version.json
 - Appends to changelog.txt
"""

import json
import datetime
import os

VERSION_FILE = "../version.json"
CHANGELOG_FILE = "../changelog.txt"

def load_version():
    with open(VERSION_FILE, "r") as f:
        return json.load(f)

def save_version(data):
    with open(VERSION_FILE, "w") as f:
        json.dump(data, f, indent=2)

def bump(version_type):
    v = load_version()
    major, minor, patch = map(int, v["version"].split("."))

    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    v["version"] = f"{major}.{minor}.{patch}"
    v["build"] += 1
    v["date"] = datetime.datetime.now().strftime("%Y-%m-%d")

    save_version(v)

    with open(CHANGELOG_FILE, "a") as f:
        f.write(f"\nv{v['version']} ({v['date']})\n- Updated firmware.\n")

    print("New version:", v["version"])

if __name__ == "__main__":
    import sys
    bump(sys.argv[1] if len(sys.argv) > 1 else "patch")

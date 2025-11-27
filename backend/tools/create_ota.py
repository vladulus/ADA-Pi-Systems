#!/usr/bin/env python3
"""
ADA-PI OTA Packaging Tool
=========================

Creates a complete OTA archive containing:
 - backend/ folder
 - requirements-frozen.txt
 - version.json
 - manifest.json
 - changelog.txt

Output:
   ADA-Pi-v{VERSION}.ota
"""

import os
import json
import tarfile
import hashlib
from datetime import datetime


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
BACKEND_DIR = "backend"
OUTPUT_DIR = "dist"
VERSION_FILE = "version.json"
CHANGELOG_FILE = "changelog.txt"
FROZEN_REQ = "backend/requirements-frozen.txt"


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_version():
    if not os.path.exists(VERSION_FILE):
        return "0.0.1"

    with open(VERSION_FILE, "r") as f:
        j = json.load(f)
        return j.get("version", "0.0.1")


def load_changelog():
    if not os.path.exists(CHANGELOG_FILE):
        return "Initial firmware.\n"
    with open(CHANGELOG_FILE) as f:
        return f.read()


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def create_manifest(version, sha256):
    manifest = {
        "version": version,
        "timestamp": int(datetime.now().timestamp()),
        "min_supported": "1.0.0",
        "device_model": "ADA-PI-RPI5",
        "sha256": sha256,
        "files": [
            "backend/",
            "requirements-frozen.txt",
            "version.json",
            "changelog.txt"
        ]
    }

    with open("manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


def build_ota():
    version = load_version()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output_file = f"{OUTPUT_DIR}/ADA-Pi-v{version}.ota"

    print(f"Creating OTA: {output_file}")

    # 1. Create tar.gz archive
    with tarfile.open(output_file, "w:gz") as tar:
        tar.add("backend", arcname="backend")
        tar.add(FROZEN_REQ, arcname="requirements-frozen.txt")

        tar.add(VERSION_FILE, arcname="version.json")
        tar.add(CHANGELOG_FILE, arcname="changelog.txt")

    # 2. Compute SHA256 and generate manifest.json
    sha = compute_sha256(output_file)
    create_manifest(version, sha)

    # 3. Add manifest.json into the same directory
    manifest_path = "manifest.json"
    final_ota = f"{OUTPUT_DIR}/ADA-Pi-v{version}.ota"

    # append manifest into final archive
    with tarfile.open(final_ota, "a:gz") as tar:
        tar.add(manifest_path, arcname="manifest.json")

    print("OTA created successfully.")
    print(f"Path: {final_ota}")
    print(f"SHA256: {sha}")


if __name__ == "__main__":
    build_ota()

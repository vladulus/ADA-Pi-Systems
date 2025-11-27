#!/usr/bin/env python3
# ADA-Pi OTA Manager (VENV-AWARE, SAFE INSTALL)
# Combines your download system + the new venv installer architecture

import os
import time
import hashlib
import requests
import shutil
import subprocess
from logger import logger
from ipc.router import router


class OTAManager:
    # OTA/LAYOUT PATHS
    OTA_DIR = "/opt/ada-pi/data/ota"
    STAGING_DIR = "/opt/ada-pi/data/ota/staging"
    BACKEND_INSTALL_DIR = "/opt/ada-pi/backend"
    VENV_DIR = "/opt/ada-pi/venv"
    CHUNK = 1024 * 256  # 256 KB chunks

    def __init__(self, storage):
        self.storage = storage
        self.running = True
        self.update_queue = []

        os.makedirs(self.OTA_DIR, exist_ok=True)
        os.makedirs(self.STAGING_DIR, exist_ok=True)

    # ------------------------------------------------------------
    # Public API called from REST endpoint /api/ota/update
    # ------------------------------------------------------------
    def queue_update(self, url: str, sha256: str = None):
        self.update_queue.append({"url": url, "sha256": sha256})
        logger.log("INFO", f"OTA queued: {url}")
        router.publish("ota_status", {"state": "queued", "url": url})

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "OTA Worker started.")
        while self.running:
            if self.update_queue:
                job = self.update_queue.pop(0)
                self._process_job(job)
            time.sleep(1)

    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # Process OTA job
    # ------------------------------------------------------------
    def _process_job(self, job):
        url = job["url"]
        sha256 = job["sha256"]

        router.publish("ota_status", {"state": "downloading", "url": url})
        file_path = self._download(url)

        if not file_path:
            router.publish("ota_status", {"state": "error", "msg": "download_failed"})
            return

        router.publish("ota_status", {"state": "downloaded", "file": file_path})

        # SHA256 verification
        if sha256:
            router.publish("ota_status", {"state": "verifying"})
            if not self._verify_sha256(file_path, sha256):
                router.publish("ota_status", {"state": "error", "msg": "sha256_mismatch"})
                return
            router.publish("ota_status", {"state": "verified"})

        # Extract package
        router.publish("ota_status", {"state": "extracting"})
        if not self._extract_to_staging(file_path):
            router.publish("ota_status", {"state": "error", "msg": "extract_failed"})
            return

        # Install backend files
        router.publish("ota_status", {"state": "installing_backend"})
        if not self._replace_backend():
            router.publish("ota_status", {"state": "error", "msg": "backend_install_failed"})
            return

        # Rebuild venv
        router.publish("ota_status", {"state": "rebuilding_venv"})
        if not self._rebuild_venv():
            router.publish("ota_status", {"state": "error", "msg": "venv_failed"})
            return

        # Restart backend
        router.publish("ota_status", {"state": "restarting"})
        if not self._restart_backend():
            router.publish("ota_status", {"state": "error", "msg": "restart_failed"})
            return

        router.publish("ota_status", {"state": "completed"})
        logger.log("INFO", "OTA update applied successfully.")

    # ------------------------------------------------------------
    # Download with resume
    # ------------------------------------------------------------
    def _download(self, url):
        filename = url.split("/")[-1]
        path = os.path.join(self.OTA_DIR, filename)

        headers = {}
        if os.path.exists(path):
            headers["Range"] = f"bytes={os.path.getsize(path)}-"

        try:
            with requests.get(url, stream=True, headers=headers, timeout=10) as r:
                r.raise_for_status()
                mode = "ab" if "Range" in headers else "wb"
                with open(path, mode) as f:
                    for chunk in r.iter_content(self.CHUNK):
                        if chunk:
                            f.write(chunk)
                return path

        except Exception as e:
            logger.log("ERROR", f"OTA download error: {e}")
            return None

    # ------------------------------------------------------------
    # SHA256 verification
    # ------------------------------------------------------------
    def _verify_sha256(self, path, expected_hash):
        logger.log("INFO", "Verifying SHA256...")
        h = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            return h.hexdigest().lower() == expected_hash.lower()
        except:
            return False

    # ------------------------------------------------------------
    # Extract OTA file (zip or tar.gz)
    # ------------------------------------------------------------
    def _extract_to_staging(self, path):
        logger.log("INFO", "Extracting OTA package...")

        shutil.rmtree(self.STAGING_DIR, ignore_errors=True)
        os.makedirs(self.STAGING_DIR, exist_ok=True)

        try:
            if path.endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(path, "r") as z:
                    z.extractall(self.STAGING_DIR)

            elif path.endswith(".tar.gz") or path.endswith(".tgz"):
                import tarfile
                with tarfile.open(path, "r:gz") as t:
                    t.extractall(self.STAGING_DIR)

            else:
                logger.log("ERROR", "Unsupported OTA format")
                return False

            return True

        except Exception as e:
            logger.log("ERROR", f"Extract error: {e}")
            return False

    # ------------------------------------------------------------
    # Replace backend folder
    # ------------------------------------------------------------
    def _replace_backend(self):
        backend_src = os.path.join(self.STAGING_DIR, "backend")
        if not os.path.exists(backend_src):
            logger.log("ERROR", "OTA missing backend/")
            return False

        try:
            shutil.rmtree(self.BACKEND_INSTALL_DIR, ignore_errors=True)
            shutil.copytree(backend_src, self.BACKEND_INSTALL_DIR)
            return True
        except Exception as e:
            logger.log("ERROR", f"Backend replace error: {e}")
            return False

    # ------------------------------------------------------------
    # Rebuild virtual environment
    # ------------------------------------------------------------
    def _rebuild_venv(self):
        req = os.path.join(self.BACKEND_INSTALL_DIR, "requirements-frozen.txt")

        try:
            shutil.rmtree(self.VENV_DIR, ignore_errors=True)
            subprocess.run(["python3", "-m", "venv", self.VENV_DIR], check=True)
            subprocess.run([f"{self.VENV_DIR}/bin/pip", "install", "-r", req], check=True)
            return True

        except Exception as e:
            logger.log("ERROR", f"Venv rebuild error: {e}")
            return False

    # ------------------------------------------------------------
    # Restart systemd backend service
    # ------------------------------------------------------------
    def _restart_backend(self):
        r = os.system("systemctl restart ada-pi-backend.service")
        return r == 0

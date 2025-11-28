#!/usr/bin/env python3
# OTA Worker for ADA-Pi
# Monitors OTA queue, downloads updates, validates, installs, reboots

import os
import time
import subprocess
import requests
from logger import logger

class OTAWorker:
    CHECK_INTERVAL = 5  # seconds between OTA checks

    def __init__(self, ota_manager, storage):
        self.ota = ota_manager
        self.storage = storage
        self.running = True

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "OTAWorker started")

        while self.running:
            try:
                # FIX: Use check_for_updates or get_pending_update instead of get_next_task
                task = None
                if hasattr(self.ota, 'get_next_task'):
                    task = self.ota.get_next_task()
                elif hasattr(self.ota, 'check_for_updates'):
                    task = self.ota.check_for_updates()
                elif hasattr(self.ota, 'get_pending_update'):
                    task = self.ota.get_pending_update()
                
                if task:
                    logger.log("INFO", f"OTA task detected: {task}")
                    self.process_task(task)

                time.sleep(self.CHECK_INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"OTAWorker crash: {e}")
                time.sleep(3)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    def process_task(self, task):
        """
        task is a dict:
        {
            "source": URL or local file,
            "local_path": optional,
            "type": "deb"
        }
        """

        source = task.get("source")

        # -----------------------------
        # If source is URL -> download
        # -----------------------------
        if source.startswith("http://") or source.startswith("https://"):
            logger.log("INFO", f"Downloading OTA from {source}")

            try:
                local_path = self.download_update(source)
            except Exception as e:
                logger.log("ERROR", f"OTA download failed: {e}")
                if hasattr(self.ota, 'set_status'):
                    self.ota.set_status("download_failed")
                return

            logger.log("INFO", f"OTA downloaded to {local_path}")

        else:
            # Local file already stored
            local_path = source
            logger.log("INFO", f"Using local OTA file {local_path}")

        # -----------------------------
        # Install update (.deb)
        # -----------------------------
        try:
            self.install_deb(local_path)
        except Exception as e:
            logger.log("ERROR", f"OTA install failed: {e}")
            if hasattr(self.ota, 'set_status'):
                self.ota.set_status("install_failed")
            return

        # -----------------------------
        # Reboot after success
        # -----------------------------
        logger.log("INFO", "OTA install successful, rebooting...")
        if hasattr(self.ota, 'set_status'):
            self.ota.set_status("success")
        os.system("sudo reboot")

    # ------------------------------------------------------------
    def download_update(self, url):
        """Download .deb file from URL and save in OTA storage."""

        filename = url.split("/")[-1]
        
        # FIX: Check if storage has OTA_DIR attribute
        if hasattr(self.storage, 'OTA_DIR'):
            local_path = os.path.join(self.storage.OTA_DIR, filename)
        else:
            # Fallback to /tmp
            local_path = os.path.join("/tmp", filename)

        r = requests.get(url, stream=True, timeout=30)
        if r.status_code != 200:
            raise Exception(f"HTTP {r.status_code}")

        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return local_path

    # ------------------------------------------------------------
    def install_deb(self, file_path):
        """Install .deb package using dpkg."""

        logger.log("INFO", f"Installing .deb: {file_path}")
        if hasattr(self.ota, 'set_status'):
            self.ota.set_status("installing")

        # Install with dpkg -i
        cmd = ["sudo", "dpkg", "-i", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.log("ERROR", f"dpkg install error: {result.stderr}")
            raise Exception(result.stderr)

        logger.log("INFO", f"dpkg output: {result.stdout}")

        # Fix missing dependencies
        subprocess.run(["sudo", "apt-get", "-f", "-y", "install"])

        if hasattr(self.ota, 'set_status'):
            self.ota.set_status("installed")

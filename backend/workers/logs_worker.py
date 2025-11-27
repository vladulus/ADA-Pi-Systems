#!/usr/bin/env python3
# ADA-Pi Logs Worker
# Reads system logs + internal logs and writes them into rotation system

import time
import os
import subprocess
from logger import logger
from ipc.router import router
from storage.storage_manager import StorageManager


class LogsWorker:
    INTERVAL = 1  # seconds

    def __init__(self, logs_module):
        self.logs = logs_module
        self.running = True
        self.storage = StorageManager()

        self.log_file = None
        self.current_date = None

        logger.log("INFO", "LogsWorker initialized")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "LogsWorker started")

        while self.running:
            try:
                self._rotate_if_needed()
                self._read_journal_tail()
                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"LogsWorker crash: {e}")
                time.sleep(2)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False
        if self.log_file:
            try: self.log_file.close()
            except: pass

    # ------------------------------------------------------------
    def _rotate_if_needed(self):
        """Rotate log file daily."""
        today = time.strftime("%Y-%m-%d")

        if today != self.current_date:
            self.current_date = today

            # close previous
            if self.log_file:
                try: self.log_file.close()
                except: pass

            # new file path
            path = self.storage.create_daily_log_file(today)
            self.log_file = open(path, "a", buffering=1)
            logger.log("INFO", f"LogsWorker: new log file {path}")

    # ------------------------------------------------------------
    def _read_journal_tail(self):
        """
        Reads last lines of system journal:
          journalctl -n 20 -o short
        """
        try:
            out = subprocess.check_output(
                ["journalctl", "-n", "20", "-o", "short"],
                stderr=subprocess.DEVNULL
            ).decode(errors="ignore")

            for line in out.strip().split("\n"):
                self._handle_line(line)

        except Exception as e:
            logger.log("ERROR", f"Failed reading system logs: {e}")

    # ------------------------------------------------------------
    def _handle_line(self, line):
        """
        Push line to:
          - LogsModule (for UI)
          - Disk log file
          - IPC
        """
        line = line.strip()
        if not line:
            return

        # push to module buffer
        self.logs.push(line)

        # write to file
        if self.log_file:
            self.log_file.write(line + "\n")

        # notify listeners
        router.publish("logs_update", {"line": line})

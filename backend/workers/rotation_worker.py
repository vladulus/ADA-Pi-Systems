import time
import threading
from datetime import datetime
from logger import logger


class RotationWorker:
    """
    Log Rotation Worker
    ===================

    Runs once per day at 02:00 AM and:
      - Rotates daily → weekly logs
      - Rotates weekly → monthly logs
      - Rotates monthly → yearly logs
      - Applies deletion rules

    Uses StorageManager for all operations.
    """

    CHECK_INTERVAL = 30        # seconds
    RUN_HOUR = 2               # 02:00 AM
    RUN_MINUTE = 0

    def __init__(self, storage_manager):
        self.storage = storage_manager
        self.running = True
        self.last_run_date = None

    # ------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "RotationWorker started. Waiting for rotation time...")

        while self.running:
            try:
                now = datetime.now()

                # run only once per day
                if (now.hour == self.RUN_HOUR and 
                    now.minute == self.RUN_MINUTE and
                    self.last_run_date != now.date()):

                    self._run_rotation()
                    self.last_run_date = now.date()

                time.sleep(self.CHECK_INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"RotationWorker error: {e}")
                time.sleep(5)

    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # PERFORM ROTATION
    # ------------------------------------------------------------
    def _run_rotation(self):
        logger.log("INFO", "Starting daily log rotation...")

        try:
            # DAILY → WEEKLY
            self.storage.rotate_daily_to_weekly()
            logger.log("INFO", "Daily → Weekly rotation OK")

            # WEEKLY → MONTHLY
            self.storage.rotate_weekly_to_monthly()
            logger.log("INFO", "Weekly → Monthly rotation OK")

            # MONTHLY → YEARLY
            self.storage.rotate_monthly_to_yearly()
            logger.log("INFO", "Monthly → Yearly rotation OK")

            # CLEANUP
            self.storage.delete_old_logs()
            logger.log("INFO", "Old log cleanup OK")

        except Exception as e:
            logger.log("ERROR", f"RotationWorker failed: {e}")

        logger.log("INFO", "Log rotation completed.")

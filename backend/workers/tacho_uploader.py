import time
import json
import requests
from logger import logger
from ipc.router import router


class TachoUploader:
    """
    Uploads tacho logs to a remote server.
    Workflow:
      - Upload *daily* logs first
      - When uploaded successfully → delete the local file
      - Weekly logs may be uploaded on schedule
      - Monthly logs uploaded optionally
      - Yearly logs are kept for archive
    """

    INTERVAL = 30   # upload check interval (seconds)

    def __init__(self, tacho_module, storage):
        self.tacho = tacho_module
        self.storage = storage
        self.running = True

    # ------------------------------------------------------------

    def start(self):
        logger.log("INFO", "TachoUploader started.")

        while self.running:
            try:
                self.process_daily_uploads()
                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"TachoUploader crash: {e}")
                time.sleep(3)

    # ------------------------------------------------------------

    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # MAIN UPLOAD LOGIC
    # ------------------------------------------------------------

    def process_daily_uploads(self):
        """
        Upload daily logs (detailed logs).
        After successful upload → delete file.
        """

        daily_files = self.storage.get_daily_logs()

        if not daily_files:
            return

        for filepath in daily_files:
            try:
                logger.log("INFO", f"Uploading tacho log: {filepath}")
                if self.upload_file(filepath):
                    logger.log("INFO", f"Tacho log uploaded OK: {filepath}")
                    self.storage.delete_file(filepath)
                    router.publish("tacho_upload_update", {
                        "file": filepath,
                        "status": "uploaded"
                    })
                else:
                    logger.log("WARN", f"Tacho log upload failed: {filepath}")

            except Exception as e:
                logger.log("ERROR", f"Error uploading {filepath}: {e}")

    # ------------------------------------------------------------
    # FILE UPLOAD
    # ------------------------------------------------------------

    def upload_file(self, filepath):
        """
        Uploads a tacho log file to the remote server via HTTP POST.
        Returns True on success, False on failure.
        """

        url = self.get_upload_url()
        if not url:
            logger.log("WARN", "No upload URL configured.")
            return False

        try:
            with open(filepath, "rb") as f:
                files = {"file": f}
                data = {
                    "device_id": self.tacho.device_id if hasattr(self.tacho, "device_id") else "ADA-PI",
                    "type": "tacho_daily"
                }

                resp = requests.post(url, files=files, data=data, timeout=15)

            if resp.status_code == 200:
                return True

            logger.log("WARN", f"Upload server error {resp.status_code}: {resp.text}")
            return False

        except Exception as e:
            logger.log("ERROR", f"Upload failed: {e}")
            return False

    # ------------------------------------------------------------

    def get_upload_url(self):
        """
        Reads tacho upload URL from configuration (future-proof).
        """
        try:
            from config_manager import load_config
            cfg = load_config()
            return cfg.get("upload_url_tacho", None)
        except:
            return None

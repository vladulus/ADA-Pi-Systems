import time
import json
import requests
import os
from logger import logger
from ipc.router import router
from config_manager import load_config
from engine.jwt_auth import create_jwt


class CloudUploader:
    """
    Cloud uploader with CONFIG CACHING.

    Loads configuration ONCE at startup and only reloads when:
      - IPC event "config_changed" is received
      - Server sends new upload_interval in response
    """

    INTERVAL = 15
    LOG_UPLOAD_INTERVAL = 300
    RETRIES = 3

    def __init__(self, modules, storage):
        self.modules = modules
        self.storage = storage
        self.running = True
        self.last_log_upload = 0

        # Cached config values
        self._load_config_cached()

        # Listen for config changes (e.g. settings updated)
        router.subscribe("config_changed", self._reload_config)

    # ------------------------------------------------------------
    # CONFIG CACHE
    # ------------------------------------------------------------

    def _load_config_cached(self):
        """Load configuration from disk ONCE."""
        cfg = load_config()

        self.device_id = cfg.get("device_id", "ADA-PI-UNKNOWN")

        # Cloud URLs are nested under "cloud" key
        cloud_cfg = cfg.get("cloud", {})
        self.cloud_url = cloud_cfg.get("upload_url", "").strip()
        self.logs_url = cloud_cfg.get("logs_url", "").strip()

        logger.log("INFO", f"CloudUploader: config loaded - device={self.device_id}, url={self.cloud_url}")

    def _reload_config(self, _=None):
        """Reload config when frontend/API updates it."""
        logger.log("INFO", "CloudUploader: configuration reload triggered")
        self._load_config_cached()

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "CloudUploader started.")

        while self.running:
            now = time.time()

            try:
                self.upload_snapshot()

                if now - self.last_log_upload > self.LOG_UPLOAD_INTERVAL:
                    self.upload_logs()
                    self.last_log_upload = now

                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"CloudUploader crash: {e}")
                time.sleep(5)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # SNAPSHOT UPLOAD
    # ------------------------------------------------------------

    def upload_snapshot(self):
        if not self.cloud_url:
            return

        if not self._online():
            logger.log("WARN", "CloudUploader: offline, skipping snapshot")
            return

        snapshot = self._build_snapshot()
        token = self._get_jwt()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        for attempt in range(self.RETRIES):
            try:
                resp = requests.post(
                    self.cloud_url,
                    headers=headers,
                    json=snapshot,
                    timeout=10
                )

                # accept all 2xx codes
                if 200 <= resp.status_code < 300:
                    router.publish("cloud_upload", {"status": "ok"})
                    
                    # Process server response
                    self._process_server_response(resp)
                    return

                logger.log(
                    "WARN",
                    f"Snapshot upload failed (try {attempt+1}/{self.RETRIES}): "
                    f"HTTP {resp.status_code}"
                )

            except Exception as e:
                logger.log(
                    "ERROR",
                    f"Snapshot upload error (try {attempt+1}/{self.RETRIES}): {e}"
                )

            time.sleep(2)

    # ------------------------------------------------------------
    # PROCESS SERVER RESPONSE
    # ------------------------------------------------------------

    def _process_server_response(self, resp):
        """Process commands and settings from server response."""
        try:
            data = resp.json()
            
            # Check for nested data structure
            if "data" in data:
                data = data["data"]
            
            # Update upload interval if provided
            new_interval = data.get("upload_interval")
            if new_interval and isinstance(new_interval, int) and new_interval != self.INTERVAL:
                self.INTERVAL = new_interval
                logger.log("INFO", f"CloudUploader: interval updated to {new_interval}s")
            
            # Process pending commands
            pending_cmd = data.get("pending_command")
            if pending_cmd:
                self._execute_command(pending_cmd)
                
        except Exception as e:
            logger.log("WARN", f"CloudUploader: failed to parse server response: {e}")

    def _execute_command(self, command):
        """Execute a command received from server."""
        logger.log("INFO", f"CloudUploader: executing command '{command}'")
        
        if command == "read_dtc":
            # Publish event for OBD worker to read DTCs
            router.publish("obd_command", {"action": "read_dtc"})
            
        elif command == "clear_dtc":
            # Publish event for OBD worker to clear DTCs
            router.publish("obd_command", {"action": "clear_dtc"})
            
        else:
            logger.log("WARN", f"CloudUploader: unknown command '{command}'")

    # ------------------------------------------------------------
    # LOG FILE UPLOAD
    # ------------------------------------------------------------

    def upload_logs(self):
        if not self.logs_url:
            logger.log("WARN", "CloudUploader: no logs_url configured")
            return

        if not self._online():
            logger.log("WARN", "CloudUploader: offline, skipping log upload")
            return

        token = self._get_jwt()
        headers = {"Authorization": f"Bearer {token}"}

        categories = [
            ("daily",   self.storage.get_daily_logs()),
            ("weekly",  self.storage.get_weekly_logs()),
            ("monthly", self.storage.get_monthly_logs()),
            ("yearly",  self.storage.get_yearly_logs()),
        ]

        for category, files in categories:
            for entry in files:

                filename = os.path.basename(entry)

                # skip already uploaded
                if self.storage.is_uploaded(category, filename):
                    continue

                # Determine full path
                if os.path.exists(entry):
                    path = entry
                else:
                    path = os.path.join(self.storage.tacho_dir, category, filename)

                if not os.path.exists(path):
                    logger.log("WARN", f"Log missing: {path}")
                    continue

                # Upload with retries
                for attempt in range(self.RETRIES):
                    try:
                        with open(path, "rb") as f:
                            resp = requests.post(
                                self.logs_url,
                                headers=headers,
                                files={"file": (filename, f)},
                                timeout=20
                            )

                        # Accept all 2xx codes
                        if 200 <= resp.status_code < 300:
                            logger.log("INFO", f"Uploaded {category} log: {filename}")
                            self.storage.mark_uploaded(category, filename)
                            break

                        logger.log(
                            "WARN",
                            f"Upload failed for {filename} (try {attempt+1}/{self.RETRIES}): "
                            f"HTTP {resp.status_code}"
                        )

                    except Exception as e:
                        logger.log(
                            "ERROR",
                            f"Upload error for {filename} (try {attempt+1}/{self.RETRIES}): {e}"
                        )

                    time.sleep(2)

    # ------------------------------------------------------------
    # SNAPSHOT BUILDER
    # ------------------------------------------------------------

    def _build_snapshot(self):
        return {
            "timestamp": int(time.time()),
            "device_id": self.device_id,
            "gps": self.modules["gps"].read_status(),
            "obd": self.modules["obd"].read_status(),
            "tacho": self.modules["tacho"].read_status(),
            "modem": self.modules["modem"].read_status(),
            "network": self.modules["network"].read_status(),
            "ups": self.modules["ups"].read_status(),
            "fan": self.modules["fan"].read_status(),
            "bluetooth": self.modules["bluetooth"].read_status(),
            "system": self.modules["system"].read_status()
        }

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def _get_jwt(self):
        payload = {"device": self.device_id}
        return create_jwt(payload, expire_minutes=15)

    def _online(self):
        try:
            modem = self.modules["modem"].read_status()
            return bool(modem.get("connected", False))
        except:
            return False

import time
from logger import logger
from ipc.router import router


class TachoWorker:
    """
    Tacho worker:
      - Combines GPS and OBD speed
      - Builds daily / weekly / monthly / yearly logs
      - Updates TachoModule
      - Publishes tacho_update WebSocket events
    """

    INTERVAL = 1  # seconds

    def __init__(self, tacho_module, gps_module):
        self.tacho = tacho_module
        self.gps = gps_module
        self.running = True

    # ------------------------------------------------------------

    def start(self):
        logger.log("INFO", "TachoWorker started.")

        while self.running:
            try:
                self.process_tacho_tick()
                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"TachoWorker crash: {e}")
                time.sleep(1)

    # ------------------------------------------------------------

    def stop(self):
        self.running = False

    # ------------------------------------------------------------

    def process_tacho_tick(self):
        """
        Called every second to:
          - Read GPS speed
          - Read OBD speed (fallback)
          - Compute final speed
          - Log the speed point
          - Publish to UI
        """

        # 1. Prefer GPS speed
        speed = self.gps.speed if hasattr(self.gps, "speed") else 0

        # 2. Fallback: OBD speed
        try:
            if speed < 1 and hasattr(self.tacho, "obd"):
                obd_speed = self.tacho.obd.speed
                if obd_speed:
                    speed = obd_speed
        except:
            pass

        # 3. Update tacho module entry
        lat = getattr(self.gps, "lat", 0)
        lon = getattr(self.gps, "lon", 0)

        self.tacho.push_speed_point(speed, lat, lon)

        # 4. Prepare DB entry (used for TachoUploader)
        point = {
            "ts": int(time.time()),
            "speed": speed,
            "lat": lat,
            "lon": lon
        }

        # 5. Store in StorageManager via module
        try:
            self.tacho.log_point(point)
        except Exception as e:
            logger.log("ERROR", f"Failed to log tacho point: {e}")

        # 6. Notify frontend
        router.publish("tacho_update", {
            "speed": speed,
            "lat": lat,
            "lon": lon,
            "ts": point["ts"]
        })

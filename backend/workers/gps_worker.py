import time
import re
from datetime import datetime, timezone
from logger import logger
from ipc.router import router
from engine.at_engine import ATCommandEngine
from modules.gps.module import GPSModule

MPH_COUNTRIES = {"US", "GB", "UK", "LR", "MM"}

def detect_country_from_gps(lat, lon):
    if 24 <= lat <= 49 and -125 <= lon <= -66:
        return "US"
    if 49 <= lat <= 61 and -8 <= lon <= 2:
        return "GB"
    if 4 <= lat <= 9 and -12 <= lon <= -7:
        return "LR"
    if 9 <= lat <= 29 and 92 <= lon <= 101:
        return "MM"
    return "OTHER"


class GPSWorker:
    INTERVAL = 2

    def __init__(self, gps_module: GPSModule, gps_port="/dev/modem-gps"):
        self.gps = gps_module
        self.running = True
        self.gps_port = gps_port
        self.engine = ATCommandEngine()
        self._gps_enabled = False
        self._connected = False

    def start(self):
        logger.log("INFO", f"GPSWorker started (port: {self.gps_port})")

        while self.running:
            try:
                if self.read_gps_at():
                    time.sleep(self.INTERVAL)
                else:
                    self.no_fix_warning()
                    time.sleep(3)
            except Exception as e:
                logger.log("ERROR", f"GPSWorker crash: {e}")
                self._connected = False
                time.sleep(3)

    def stop(self):
        self.running = False

    def read_gps_at(self):
        try:
            if not self._connected or self.engine.ser is None:
                if not self._connect_engine():
                    return False

            if not self._gps_enabled:
                self.engine.send("AT+CGPS=1")
                self._gps_enabled = True
                logger.log("INFO", "GPS enabled")

            resp = self.engine.send("AT+CGPSINFO")
            if not resp:
                return False

            resp_text = "\n".join(resp)
            match = re.search(r'\+CGPSINFO:\s*(.+)', resp_text)
            if not match:
                return False

            data = match.group(1).strip()
            parts = data.split(',')

            if len(parts) < 4 or not parts[0]:
                return False

            lat = self._nmea_to_decimal(parts[0], parts[1])
            lon = self._nmea_to_decimal(parts[2], parts[3])

            if lat is None or lon is None:
                return False

            alt = float(parts[6]) if len(parts) > 6 and parts[6] else 0.0
            speed_knots = float(parts[7]) if len(parts) > 7 and parts[7] else 0.0
            heading = float(parts[8]) if len(parts) > 8 and parts[8] else 0.0
            speed_kmh = speed_knots * 1.852

            date_str = parts[4] if len(parts) > 4 else ""
            time_str = parts[5] if len(parts) > 5 else ""
            timestamp = datetime.now(timezone.utc).isoformat()
            if date_str and time_str:
                try:
                    time_clean = time_str.split(".")[0].ljust(6, "0")
                    timestamp = datetime.strptime(date_str + time_clean, "%d%m%y%H%M%S").replace(tzinfo=timezone.utc).isoformat()
                except:
                    pass

            logger.log("INFO", f"GPS fix: {lat:.6f}, {lon:.6f}, alt={alt}m")
            self.update_gps(lat, lon, alt, speed_kmh, 0, True, heading=heading, timestamp=timestamp)
            return True

        except Exception as e:
            logger.log("ERROR", f"GPS AT error: {e}")
            self._connected = False
            return False

    def _connect_engine(self):
        try:
            if self.engine.connect(self.gps_port, 115200):
                if self.engine.test():
                    logger.log("INFO", f"GPS connected to {self.gps_port}")
                    self._connected = True
                    return True
                self.engine.disconnect()
        except Exception as e:
            logger.log("DEBUG", f"GPS connect failed: {e}")
        
        logger.log("WARN", f"Could not connect GPS to {self.gps_port}")
        return False

    def update_gps(self, lat, lon, alt, speed, satellites, fix, hdop=None, heading=None, timestamp=None):
        country = detect_country_from_gps(lat, lon)
        auto_unit = "mph" if country in MPH_COUNTRIES else "kmh"
        self.gps.set_auto_unit(auto_unit)

        self.gps.update_position(lat, lon, alt, hdop=hdop, heading=heading, timestamp=timestamp)
        self.gps.update_speed(speed)
        self.gps.update_fix(fix)
        self.gps.satellites = satellites

        router.publish("gps_update", {
            "latitude": lat,
            "longitude": lon,
            "altitude": alt,
            "speed": self.gps.get_speed(),
            "unit": self.gps.get_unit(),
            "satellites": satellites,
            "fix": fix,
            "heading": heading,
            "timestamp": timestamp
        })

    def _nmea_to_decimal(self, value, direction):
        if not value:
            return None
        try:
            deg_len = 2 if direction in ["N", "S"] else 3
            deg = float(value[:deg_len])
            minutes = float(value[deg_len:])
            dec = deg + (minutes / 60.0)
            if direction in ["S", "W"]:
                dec = -dec
            return dec
        except:
            return None

    def no_fix_warning(self):
        self.gps.update_fix(False)
        router.publish("gps_update", {"fix": False})

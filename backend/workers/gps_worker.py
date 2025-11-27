import time
import os
import subprocess
import serial
from logger import logger
from ipc.router import router
from datetime import datetime

from modules.gps.module import GPSModule

MPH_COUNTRIES = {
    "US", "GB", "UK", "LR", "MM"
}

def detect_country_from_gps(lat, lon):
    # USA
    if 24 <= lat <= 49 and -125 <= lon <= -66:
        return "US"
    # UK
    if 49 <= lat <= 61 and -8 <= lon <= 2:
        return "GB"
    # Liberia
    if 4 <= lat <= 9 and -12 <= lon <= -7:
        return "LR"
    # Myanmar
    if 9 <= lat <= 29 and 92 <= lon <= 101:
        return "MM"
    return "OTHER"


class GPSWorker:
    INTERVAL = 1
    NMEA_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    UART_PORTS = []  # Disabled - use USB GPS only

    def __init__(self, gps_module: GPSModule):
        self.gps = gps_module
        self.running = True
        self.mode = None
        self.ser = None

    # -------------------------------------------------------------
    def start(self):
        logger.log("INFO", "GPSWorker started.")

        while self.running:
            try:
                if self.try_modem_gnss():
                    self.mode = "MODEM"
                    time.sleep(self.INTERVAL)
                    continue

                if self.try_usb_gps():
                    self.mode = "USB"
                    time.sleep(self.INTERVAL)
                    continue

                if self.try_uart_gps():
                    self.mode = "UART"
                    time.sleep(self.INTERVAL)
                    continue

                self.no_fix_warning()
                time.sleep(2)

            except Exception as e:
                logger.log("ERROR", f"GPSWorker crash: {e}")
                time.sleep(2)

    # -------------------------------------------------------------
    def stop(self):
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass

    # -------------------------------------------------------------
    def try_modem_gnss(self):
        try:
            out = subprocess.check_output(["mmcli", "-L"]).decode()
            if "/" not in out:
                return False

            line = out.strip().split("\n")[0]
            modem_index = line.split("/")[-1].split()[0]

            subprocess.call(["mmcli", "-m", modem_index, "--location-enable-gps-nmea"])

            loc = subprocess.check_output(
                ["mmcli", "-m", modem_index, "--location-get"]
            ).decode()

            lat = self._extract("latitude", loc)
            lon = self._extract("longitude", loc)
            alt = self._extract("altitude", loc)
            spd = self._extract("speed", loc)

            if not lat or not lon:
                return False

            self.update_gps(float(lat), float(lon), float(alt or 0), float(spd or 0), True)
            return True
        except:
            return False

    # -------------------------------------------------------------
    def try_usb_gps(self):
        for port in self.NMEA_PORTS:
            if os.path.exists(port):
                return self._read_nmea(port)
        return False

    # -------------------------------------------------------------
    def try_uart_gps(self):
        for port in self.UART_PORTS:
            if os.path.exists(port):
                return self._read_nmea(port)
        return False

    # -------------------------------------------------------------
    def _read_nmea(self, port):
        try:
            if not self.ser or self.ser.port != port:
                self.ser = serial.Serial(port, 9600, timeout=1)
                logger.log("INFO", f"NMEA GPS connected on {port}")

            line = self.ser.readline().decode(errors="ignore").strip()

            if not line.startswith("$"):
                return True

            if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                parts = line.split(",")
                if parts[6] == "0":
                    return True  # no fix

                lat = self._nmea_to_decimal(parts[2], parts[3])
                lon = self._nmea_to_decimal(parts[4], parts[5])
                alt = float(parts[9]) if parts[9] else 0.0

                self.update_gps(lat, lon, alt, self.gps.speed_kmh, True)

            if line.startswith("$GPRMC") or line.startswith("$GNRMC"):
                parts = line.split(",")
                if parts[2] != "A":
                    return True
                speed_knots = float(parts[7]) if parts[7] else 0
                speed_kmh = speed_knots * 1.852
                self.gps.update_speed(speed_kmh)

        except:
            return False

        return True

    # -------------------------------------------------------------
    def update_gps(self, lat, lon, alt, speed, fix):
        # Auto-detect units
        country = detect_country_from_gps(lat, lon)
        auto_unit = "mph" if country in MPH_COUNTRIES else "kmh"
        self.gps.set_auto_unit(auto_unit)

        # Update module
        self.gps.update_position(lat, lon, alt)
        self.gps.update_speed(speed)
        self.gps.update_fix(fix)

        # Notify frontend
        router.publish("gps_update", {
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "speed": self.gps.get_speed(),
            "unit": self.gps.get_unit(),
            "fix": fix
        })

    # -------------------------------------------------------------
    def _extract(self, key, text):
        if key not in text:
            return None
        try:
            return text.split(key)[1].split("\n")[0].replace(":", "").strip()
        except:
            return None

    def _nmea_to_decimal(self, value, direction):
        if not value:
            return None
        deg = float(value[:2])
        minutes = float(value[2:])
        dec = deg + (minutes / 60.0)
        if direction in ["S", "W"]:
            dec = -dec
        return dec

    # -------------------------------------------------------------
    def no_fix_warning(self):
        self.gps.update_fix(False)
        router.publish("gps_update", {"fix": False})
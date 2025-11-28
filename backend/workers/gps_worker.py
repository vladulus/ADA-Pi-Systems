import time
import subprocess
import re
from datetime import datetime, timezone
from logger import logger
from ipc.router import router

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
    """GPS Worker - Modem GPS only (Quectel/Simcom)"""

    INTERVAL = 1

    def __init__(self, gps_module: GPSModule):
        self.gps = gps_module
        self.running = True
        self.modem_index = None
        self._gps_enabled = False

    # -------------------------------------------------------------
    def start(self):
        logger.log("INFO", "GPSWorker started (modem GPS mode)")

        while self.running:
            try:
                if self.read_modem_gps():
                    time.sleep(self.INTERVAL)
                else:
                    # No fix
                    self.no_fix_warning()
                    time.sleep(2)

            except Exception as e:
                logger.log("ERROR", f"GPSWorker crash: {e}")
                time.sleep(2)

    # -------------------------------------------------------------
    def stop(self):
        self.running = False

    # -------------------------------------------------------------
    def read_modem_gps(self):
        """Read GPS data from Quectel/Simcom modem via mmcli"""
        try:
            # Detect modem (only once)
            if self.modem_index is None:
                out = subprocess.check_output(
                    ["mmcli", "-L"],
                    stderr=subprocess.DEVNULL
                ).decode()

                if "/" not in out:
                    return False

                line = out.strip().split("\n")[0]
                self.modem_index = line.split("/")[-1].split()[0]
                logger.log("INFO", f"Modem detected: {self.modem_index}")

            # Enable GPS (only once)
            if not self._gps_enabled:
                result = subprocess.call(
                    ["mmcli", "-m", self.modem_index, "--location-enable-gps-nmea"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result == 0:
                    self._gps_enabled = True
                    logger.log("INFO", f"GPS enabled on modem {self.modem_index}")
                else:
                    logger.log("WARN", "Failed to enable GPS on modem")
                    return False

            # Get current location
            loc = subprocess.check_output(
                ["mmcli", "-m", self.modem_index, "--location-get"],
                stderr=subprocess.DEVNULL
            ).decode()

            # Parse NMEA sentences
            if "nmea:" not in loc:
                logger.log("WARN", "No NMEA data in mmcli output")

            # Fallback: parse mmcli key/value location lines (latitude/longitude/altitude)
            lat_field = None
            lon_field = None
            alt_field = None

            for line in loc.split("\n"):
                lower_line = line.lower()
                if "latitude" in lower_line:
                    m = re.search(r"latitude:\s*([-+]?\d+(?:\.\d+)?)", lower_line)
                    if m:
                        lat_field = float(m.group(1))
                if "longitude" in lower_line:
                    m = re.search(r"longitude:\s*([-+]?\d+(?:\.\d+)?)", lower_line)
                    if m:
                        lon_field = float(m.group(1))
                if "altitude" in lower_line:
                    m = re.search(r"altitude:\s*([-+]?\d+(?:\.\d+)?)", lower_line)
                    if m:
                        alt_field = float(m.group(1))

            # Extract all lines containing NMEA sentences
            # Format: "GPS | nmea: $GPGSA,..." or "     |         $GNGNS,..."
            nmea_lines = []
            for line in loc.split("\n"):
                # Check if line contains a $ (NMEA sentence marker)
                if "$" in line:
                    # Extract the part after $ (might have leading spaces/pipes)
                    sentence = line[line.index("$"):].strip()
                    if sentence.startswith("$"):
                        nmea_lines.append(sentence)

            logger.log("DEBUG", f"Found {len(nmea_lines)} NMEA sentences")

            # Parse position from common NMEA messages (GNS/GGA for position, RMC for speed/heading)
            lat, lon, alt, speed_kmh = None, None, 0.0, 0.0
            satellites = None
            hdop = None
            heading = None
            timestamp = None
            fix_state = False

            for nmea in nmea_lines:
                # GNGNS or GPGNS: $G?GNS,time,lat,N,lon,W,mode,sats,hdop,alt,sep,...
                if nmea.startswith("$GNGNS") or nmea.startswith("$GPGNS"):
                    parts = nmea.split(",")
                    if len(parts) >= 10 and parts[6] != "N":  # N = no fix
                        lat = self._nmea_to_decimal(parts[2], parts[3]) if lat is None else lat
                        lon = self._nmea_to_decimal(parts[4], parts[5]) if lon is None else lon
                        satellites = int(parts[7]) if parts[7] else satellites
                        alt = float(parts[9]) if parts[9] else alt
                        hdop = float(parts[8]) if parts[8] else hdop
                        fix_state = True

                # GPGGA / GNGGA: $G?GGA,time,lat,N,lon,E,fix,sats,hdop,alt,alt_unit,sep,sep_unit,...
                elif nmea.startswith("$GPGGA") or nmea.startswith("$GNGGA"):
                    parts = nmea.split(",")
                    if len(parts) >= 10 and parts[6] not in ["", "0"]:
                        lat = self._nmea_to_decimal(parts[2], parts[3]) if lat is None else lat
                        lon = self._nmea_to_decimal(parts[4], parts[5]) if lon is None else lon
                        satellites = int(parts[7]) if parts[7] else satellites
                        hdop = float(parts[8]) if parts[8] else hdop
                        alt = float(parts[9]) if parts[9] else alt
                        fix_state = True

                # GPRMC / GNRMC: speed/heading/date/time/lat/lon
                elif nmea.startswith("$GPRMC") or nmea.startswith("$GNRMC"):
                    parts = nmea.split(",")
                    if len(parts) >= 10 and parts[2] == "A":  # A = active fix
                        lat = self._nmea_to_decimal(parts[3], parts[4]) if len(parts) > 4 and parts[3] else lat
                        lon = self._nmea_to_decimal(parts[5], parts[6]) if len(parts) > 6 and parts[5] else lon
                        fix_state = True

                        if parts[7]:
                            speed_knots = float(parts[7])
                            speed_kmh = speed_knots * 1.852

                        if parts[8]:
                            heading = float(parts[8])

                        time_str = parts[1]
                        date_str = parts[9]
                        if time_str and date_str:
                            try:
                                # Strip fractional seconds if present
                                time_clean = time_str.split(".")[0].ljust(6, "0")
                                timestamp = datetime.strptime(date_str + time_clean, "%d%m%y%H%M%S").replace(tzinfo=timezone.utc).isoformat()
                            except ValueError:
                                timestamp = None

            # Use mmcli key/value fallback if NMEA parsing didn't fill coordinates (or when NMEA is absent)
            if lat is None and lat_field is not None:
                lat = lat_field
                fix_state = True
            if lon is None and lon_field is not None:
                lon = lon_field
                fix_state = True
            if alt in [None, 0.0] and alt_field is not None:
                alt = alt_field

            # If there were no NMEA lines at all but we got mmcli coordinates, keep going
            if not nmea_lines and lat is not None and lon is not None:
                logger.log("WARN", "No NMEA sentences parsed, using mmcli coordinates")

            if lat is None or lon is None:
                logger.log("WARN", f"Failed to parse GPS coordinates (found {len(nmea_lines)} NMEA lines)")
                return False

            # Fallback defaults
            if satellites is None:
                satellites = 0
            if alt is None:
                alt = 0.0
            if timestamp is None:
                timestamp = datetime.now(timezone.utc).isoformat()

            fix_state = fix_state or False

            logger.log("INFO", f"GPS fix: {lat:.6f}, {lon:.6f}, {satellites} sats")

            # Update GPS module
            self.update_gps(lat, lon, alt, speed_kmh, satellites, fix_state, hdop=hdop, heading=heading, timestamp=timestamp)
            return True

        except subprocess.CalledProcessError:
            # Modem disconnected
            self.modem_index = None
            self._gps_enabled = False
            return False
        except Exception as e:
            logger.log("ERROR", f"Modem GPS error: {e}")
            return False

    # -------------------------------------------------------------
    def update_gps(self, lat, lon, alt, speed, satellites, fix, hdop=None, heading=None, timestamp=None):
        """Update GPS module and notify frontend"""

        # Auto-detect speed units
        country = detect_country_from_gps(lat, lon)
        auto_unit = "mph" if country in MPH_COUNTRIES else "kmh"
        self.gps.set_auto_unit(auto_unit)

        # Update module with correct methods
        self.gps.update_position(lat, lon, alt, hdop=hdop, heading=heading, timestamp=timestamp)
        self.gps.update_speed(speed)
        self.gps.update_fix(fix)
        # Set satellites count directly (no method for int)
        self.gps.satellites = satellites

        # Notify frontend
        router.publish("gps_update", {
            "latitude": lat,
            "longitude": lon,
            "altitude": alt,
            "hdop": hdop,
            "speed": self.gps.get_speed(),
            "unit": self.gps.get_unit(),
            "satellites": satellites,
            "fix": fix,
            "heading": heading,
            "timestamp": timestamp
        })

        logger.log("DEBUG", f"GPS module updated: fix={self.gps.fix}, lat={self.gps.latitude}")

    # -------------------------------------------------------------
    def _nmea_to_decimal(self, value, direction):
        """Convert NMEA coordinate to decimal degrees."""
        if not value:
            return None

        try:
            deg_len = 2 if direction in ["N", "S"] else 3
            if len(value) <= deg_len:
                return None

            deg = float(value[:deg_len])
            minutes = float(value[deg_len:])
            dec = deg + (minutes / 60.0)

            if direction in ["S", "W"]:
                dec = -dec

            return dec
        except ValueError:
            logger.log("WARN", f"Invalid NMEA coordinate: {value}{direction}")
            return None

    # -------------------------------------------------------------
    def no_fix_warning(self):
        """Update GPS with no fix status"""
        self.gps.update_fix(False)
        router.publish("gps_update", {"fix": False})

import time
import subprocess
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
                return False

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
            
            if not nmea_lines:
                logger.log("WARN", "No NMEA sentences parsed")
                return False

            # Parse position from GNGNS or GPRMC
            lat, lon, alt, speed_kmh = None, None, 0.0, 0.0
            satellites = 0
            
            for nmea in nmea_lines:
                # GNGNS: $GNGNS,time,lat,N,lon,W,mode,sats,hdop,alt,sep,...
                if nmea.startswith("$GNGNS"):
                    parts = nmea.split(",")
                    if len(parts) >= 10 and parts[6] != "N":  # N = no fix
                        lat = self._nmea_to_decimal(parts[2], parts[3])
                        lon = self._nmea_to_decimal(parts[4], parts[5])
                        satellites = int(parts[7]) if parts[7] else 0
                        alt = float(parts[9]) if parts[9] else 0.0
                
                # GPRMC: get speed
                elif nmea.startswith("$GPRMC"):
                    parts = nmea.split(",")
                    if len(parts) >= 8 and parts[2] == "A":
                        if parts[7]:
                            speed_knots = float(parts[7])
                            speed_kmh = speed_knots * 1.852

            if lat is None or lon is None:
                logger.log("WARN", f"Failed to parse GPS coordinates (found {len(nmea_lines)} NMEA lines)")
                return False

            logger.log("INFO", f"GPS fix: {lat:.6f}, {lon:.6f}, {satellites} sats")
            
            # Update GPS module
            self.update_gps(lat, lon, alt, speed_kmh, satellites, True)
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
    def update_gps(self, lat, lon, alt, speed, satellites, fix):
        """Update GPS module and notify frontend"""
        
        # Auto-detect speed units
        country = detect_country_from_gps(lat, lon)
        auto_unit = "mph" if country in MPH_COUNTRIES else "kmh"
        self.gps.set_auto_unit(auto_unit)

        # Update module with correct methods
        self.gps.update_position(lat, lon, alt)
        self.gps.update_speed(speed)
        self.gps.update_fix(fix)
        # Set satellites count directly (no method for int)
        self.gps.satellites = satellites

        # Notify frontend
        router.publish("gps_update", {
            "latitude": lat,
            "longitude": lon,
            "altitude": alt,
            "speed": self.gps.get_speed(),
            "unit": self.gps.get_unit(),
            "satellites": satellites,
            "fix": fix
        })
        
        logger.log("DEBUG", f"GPS module updated: fix={self.gps.fix}, lat={self.gps.latitude}")

    # -------------------------------------------------------------
    def _nmea_to_decimal(self, value, direction):
        """Convert NMEA coordinate to decimal degrees"""
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
        """Update GPS with no fix status"""
        self.gps.update_fix(False)
        router.publish("gps_update", {"fix": False})

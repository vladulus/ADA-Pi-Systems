# ADA-Pi Backend Module: GPS Module
# Provides GNSS data, satellite information, and automatic km/h/mph switching.

class GPSModule:
    def __init__(self):
        # GNSS core data
        self.fix = False
        self.satellites = 0
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.hdop = 0.0
        self.speed_kmh = 0.0    # speed always stored internally as km/h
        self.heading = 0.0
        self.timestamp = None
        self.sat_list = []      # [ { azimuth, elevation, snr, constellation }, ... ]

        # Unit selection
        self.unit_mode = "auto"   # auto / kmh / mph
        self.unit_auto = "kmh"    # backend-detected unit

    # ------------------------------------------------------------
    # STATUS (used by frontend)
    # ------------------------------------------------------------
    def read_status(self):
        return {
            "fix": self.fix,
            "satellites": self.satellites,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "hdop": self.hdop,
            "speed": self.get_speed(),
            "unit": self.get_unit(),
            "heading": self.heading,
            "timestamp": self.timestamp
        }

    # ------------------------------------------------------------
    # SATELLITE LIST
    # ------------------------------------------------------------
    def read_satellites(self):
        return self.sat_list

    # ------------------------------------------------------------
    # UPDATE METHODS
    # ------------------------------------------------------------
    def update_position(self, lat, lon, alt, hdop=None, heading=None, timestamp=None):
        self.latitude = lat
        self.longitude = lon
        self.altitude = alt
        if hdop is not None:
            self.hdop = hdop
        if heading is not None:
            self.heading = heading
        if timestamp is not None:
            self.timestamp = timestamp

    def update_fix(self, fix_state):
        self.fix = fix_state

    def update_satellite_list(self, satellites):
        self.sat_list = satellites
        self.satellites = len(satellites)

    def update_speed(self, speed_kmh):
        """GPSWorker will call this and always pass km/h"""
        self.speed_kmh = speed_kmh

    # ------------------------------------------------------------
    # UNIT HANDLING
    # ------------------------------------------------------------
    def get_unit(self):
        """Return the effective unit visible to frontend"""
        if self.unit_mode == "auto":
            return self.unit_auto
        return self.unit_mode  # kmh or mph

    def get_speed(self):
        """Return speed in km/h or mph based on selected mode."""
        unit = self.get_unit()
        if unit == "mph":
            return round(self.speed_kmh * 0.621371, 1)
        return round(self.speed_kmh, 1)

    def set_unit_mode(self, mode):
        """User selection: auto / kmh / mph"""
        if mode in ["auto", "kmh", "mph"]:
            self.unit_mode = mode

    def set_auto_unit(self, auto_unit):
        """Backend auto-detection (GPS-based)"""
        if auto_unit in ["kmh", "mph"]:
            self.unit_auto = auto_unit

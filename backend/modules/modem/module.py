#!/usr/bin/env python3
# ADA-Pi Modem Module
# Stores modem state for SIMCom + Quectel modems with 5G support
import time
class ModemModule:
    def __init__(self):
        self.brand = None        # SIMCom / Quectel
        self.model = None        # SIM7600 / EC25 / EG25 / RG500Q etc.
        self.imei = None
        self.iccid = None
        self.imsi = None
        self.operator = None
        # Registration state ("registered", "searching", "denied", "offline")
        self.registration = None
        # Connection mode: 2G / 3G / 4G / 5G / unknown
        self.network_mode = None
        # Signal metrics
        self.rssi = None
        self.rsrp = None
        self.rsrq = None
        self.sinr = None
        # Bands
        self.band = None
        # Last known AT port
        self.at_port = None
        # Connection state
        self.connected = False
        # Data usage in MB
        self.data_used = 0.0
        # Error message if something fails
        self.error = None
        # Last update timestamp
        self.timestamp = 0
    # ------------------------------------------------------------
    def update(self, data: dict):
        """Update modem state with parsed worker data."""
        for key, value in data.items():
            setattr(self, key, value)
        self.timestamp = int(time.time())
    # ------------------------------------------------------------
    def read_status(self):
        """Return a clean JSON-friendly structure for UI + API."""
        return {
            "brand": self.brand,
            "model": self.model,
            "imei": self.imei,
            "iccid": self.iccid,
            "imsi": self.imsi,
            "operator": self.operator,
            "registration": self.registration,
            "network_mode": self.network_mode,
            "signal": {
                "rssi": self.rssi,
                "rsrp": self.rsrp,
                "rsrq": self.rsrq,
                "sinr": self.sinr
            },
            "band": self.band,
            "at_port": self.at_port,
            "connected": self.connected,
            "data_used": self.data_used,
            "error": self.error,
            "timestamp": self.timestamp
        }

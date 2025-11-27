#!/usr/bin/env python3
# ADA-Pi OBD Module
# Stores OBD-II state for gasoline, diesel, vans, and trucks (J1939 capable)

import time

class OBDModule:
    def __init__(self):
        # Connection info
        self.connected = False
        self.port = None
        self.baud = None
        self.protocol = None
        self.error = None
        self.timestamp = 0

        # Standard PIDs (works for all OBD-II cars)
        self.rpm = 0
        self.speed = 0
        self.coolant = 0
        self.load = 0
        self.voltage = 0.0
        self.throttle = 0
        self.fuel_level = 0
        self.intake_temp = 0
        self.maf = 0
        self.map = 0

        # Diesel PIDs (for vans & trucks)
        self.boost_pressure = 0
        self.rail_pressure = 0
        self.egr = 0
        self.dpf_temp_in = 0
        self.dpf_temp_out = 0
        self.dpf_soot = 0

        # Fault codes list
        self.fault_codes = []

    # ------------------------------------------------------------
    def update_connection(self, connected, port=None, baud=None, protocol=None, error=None):
        self.connected = connected
        self.port = port
        self.baud = baud
        self.protocol = protocol
        self.error = error
        self.timestamp = int(time.time())

    # ------------------------------------------------------------
    def update_values(self, **kwargs):
        """
        Update standard and diesel PIDs.
        Example:
           update_values(rpm=900, speed=45, coolant=80)
        """

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.timestamp = int(time.time())

    # ------------------------------------------------------------
    def update_fault_codes(self, dtc_list):
        """Update detected DTC codes."""
        self.fault_codes = dtc_list
        self.timestamp = int(time.time())

    # ------------------------------------------------------------
    def read_status(self):
        """Return JSON-friendly dictionary for API + UI."""

        return {
            "connected": self.connected,
            "port": self.port,
            "baud": self.baud,
            "protocol": self.protocol,
            "error": self.error,
            "timestamp": self.timestamp,

            "values": {
                "rpm": self.rpm,
                "speed": self.speed,
                "coolant": self.coolant,
                "load": self.load,
                "voltage": self.voltage,
                "throttle": self.throttle,
                "fuel_level": self.fuel_level,
                "intake_temp": self.intake_temp,
                "maf": self.maf,
                "map": self.map,

                # Diesel metrics
                "boost_pressure": self.boost_pressure,
                "rail_pressure": self.rail_pressure,
                "egr": self.egr,
                "dpf_temp_in": self.dpf_temp_in,
                "dpf_temp_out": self.dpf_temp_out,
                "dpf_soot": self.dpf_soot
            },

            "dtc": self.fault_codes
        }

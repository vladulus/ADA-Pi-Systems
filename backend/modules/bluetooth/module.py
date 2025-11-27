#!/usr/bin/env python3
# ADA-Pi Bluetooth Module
# Stores Bluetooth adapter state, paired devices, discovered devices

import time


class BluetoothModule:
    def __init__(self):
        # Adapter state
        self.powered = False
        self.discoverable = False
        self.mac_address = None
        self.timestamp = 0

        # Device lists
        # Example entries:
        # { mac, name, connected, rssi, battery(optional) }
        self.paired_devices = []
        self.available_devices = []

        # Error or info message
        self.error = None

    # ------------------------------------------------------------
    def read_status(self):
        """Return a JSON-friendly snapshot for API/UI."""
        return {
            "powered": self.powered,
            "discoverable": self.discoverable,
            "mac": self.mac_address,
            "paired": self.paired_devices,
            "available": self.available_devices,
            "error": self.error,
            "timestamp": self.timestamp
        }

    # ------------------------------------------------------------
    def update_adapter(self, powered=None, discoverable=None, mac=None, error=None):
        """Update adapter-level info."""
        if powered is not None:
            self.powered = powered
        if discoverable is not None:
            self.discoverable = discoverable
        if mac is not None:
            self.mac_address = mac
        if error is not None:
            self.error = error

        self.timestamp = int(time.time())

    # ------------------------------------------------------------
    def update_devices(self, paired, available):
        """Update device lists."""
        self.paired_devices = paired
        self.available_devices = available
        self.timestamp = int(time.time())

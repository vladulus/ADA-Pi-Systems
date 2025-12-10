#!/usr/bin/env python3
# ADA-Pi Bluetooth Worker
# Uses BlueZ over DBus for scanning, pairing, connecting, and status updates

import time
from logger import logger
from ipc.router import router
from engine.bluetooth_dbus import BluetoothDBus


class BluetoothWorker:
    INTERVAL = 5  # seconds between scans

    def __init__(self, bt_module):
        self.bt = bt_module
        self.running = True
        self.dbus = BluetoothDBus()

        # Commands triggered by REST API
        self.cmd_pair = None
        self.cmd_remove = None
        self.cmd_connect = None
        self.cmd_disconnect = None
        self.cmd_set_power = None       # True/False
        self.cmd_set_discoverable = None

        # Listen for config changes from cloud
        router.subscribe("bluetooth_config_changed", self._on_config_changed)

    def _on_config_changed(self, config):
        """Handle bluetooth config updates from cloud."""
        logger.log("INFO", f"BluetoothWorker: config changed from cloud: {config}")
        
        if "enabled" in config:
            self.cmd_set_power = config["enabled"]
        
        if "discoverable" in config:
            self.cmd_set_discoverable = config["discoverable"]

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "BluetoothWorker started.")

        while self.running:
            try:
                self._process_commands()
                self._update_status()
                self._refresh_devices()
            except Exception as e:
                logger.log("ERROR", f"BluetoothWorker error: {e}")

            time.sleep(self.INTERVAL)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # EXECUTE COMMANDS FROM API
    # ------------------------------------------------------------
    def _process_commands(self):

        # Power toggle
        if self.cmd_set_power is not None:
            state = bool(self.cmd_set_power)
            success = self.dbus.set_power(state)
            logger.log("INFO", f"BT Power -> {state}")
            self.bt.powered = state
            self.cmd_set_power = None

        # Discoverable toggle
        if self.cmd_set_discoverable is not None:
            state = bool(self.cmd_set_discoverable)
            success = self.dbus.set_discoverable(state)
            logger.log("INFO", f"BT Discoverable -> {state}")
            self.bt.discoverable = state
            self.cmd_set_discoverable = None

        # Pair device
        if self.cmd_pair:
            mac = self.cmd_pair
            logger.log("INFO", f"Pairing with {mac}")
            ok = self.dbus.pair(mac)
            self.cmd_pair = None

        # Remove paired device
        if self.cmd_remove:
            mac = self.cmd_remove
            logger.log("INFO", f"Removing {mac}")
            ok = self.dbus.remove(mac)
            self.cmd_remove = None

        # Connect
        if self.cmd_connect:
            mac = self.cmd_connect
            logger.log("INFO", f"Connecting to {mac}")
            ok = self.dbus.connect(mac)
            self.cmd_connect = None

        # Disconnect
        if self.cmd_disconnect:
            mac = self.cmd_disconnect
            logger.log("INFO", f"Disconnecting {mac}")
            ok = self.dbus.disconnect(mac)
            self.cmd_disconnect = None

    # ------------------------------------------------------------
    # UPDATE ADAPTER STATUS
    # ------------------------------------------------------------
    def _update_status(self):
        """Sync adapter status into module."""

        powered = self.dbus.get_power()
        discoverable = self.dbus.get_discoverable()

        self.bt.powered = powered
        self.bt.discoverable = discoverable

    # ------------------------------------------------------------
    # REFRESH DEVICES
    # ------------------------------------------------------------
    def _refresh_devices(self):
        """Refresh lists of paired + available devices."""

        all_dev = self.dbus.list_devices()

        paired = []
        available = []

        for d in all_dev:
            entry = {
                "mac": d["mac"],
                "name": d["name"],
                "connected": d["connected"],
                "rssi": d["rssi"]
            }
            if d["paired"]:
                paired.append(entry)
            else:
                available.append(entry)

        self.bt.paired_devices = paired
        self.bt.available_devices = available

        # Send event to UI
        router.publish("bt_update", {
            "powered": self.bt.powered,
            "discoverable": self.bt.discoverable,
            "paired": paired,
            "available": available
        })

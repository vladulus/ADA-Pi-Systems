#!/usr/bin/env python3
# Bluetooth BlueZ DBus Engine for ADA-Pi
# Provides a clean interface for power, scanning, pairing, and connections

import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from logger import logger


class BluetoothDBus:
    """
    Wrapper for BlueZ over D-Bus.
    Supports:
        - Power ON/OFF
        - Discoverable ON/OFF
        - Scan for devices
        - List paired devices
        - Pair / remove
        - Connect / disconnect
        - BLE RSSI / services
    """

    BLUEZ_SERVICE = "org.bluez"
    ADAPTER_IFACE = "org.bluez.Adapter1"
    DEVICE_IFACE = "org.bluez.Device1"
    AGENT_IFACE = "org.bluez.Agent1"

    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        self.adapter = self._find_adapter()

        if not self.adapter:
            logger.log("ERROR", "No Bluetooth adapter found via DBus")

    # ------------------------------------------------------------
    def _find_adapter(self):
        """Get the first available adapter."""
        try:
            manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                "org.freedesktop.DBus.ObjectManager"
            )
            objects = manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if self.ADAPTER_IFACE in interfaces:
                    return path
        except Exception as e:
            logger.log("ERROR", f"DBus adapter scan failed: {e}")
        return None

    # ------------------------------------------------------------
    # POWER
    # ------------------------------------------------------------
    def set_power(self, state: bool):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
            props.Set(self.ADAPTER_IFACE, "Powered", dbus.Boolean(state))
            return True
        except Exception as e:
            logger.log("ERROR", f"Failed to set BT power: {e}")
            return False

    def get_power(self):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
            return bool(props.Get(self.ADAPTER_IFACE, "Powered"))
        except:
            return False

    # ------------------------------------------------------------
    # DISCOVERABLE
    # ------------------------------------------------------------
    def set_discoverable(self, state: bool):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
            props.Set(self.ADAPTER_IFACE, "Discoverable", dbus.Boolean(state))
            return True
        except Exception as e:
            logger.log("ERROR", f"Failed to set discoverable: {e}")
            return False

    def get_discoverable(self):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            props = dbus.Interface(adapter_obj, "org.freedesktop.DBus.Properties")
            return bool(props.Get(self.ADAPTER_IFACE, "Discoverable"))
        except:
            return False

    # ------------------------------------------------------------
    # SCANNING
    # ------------------------------------------------------------
    def start_scan(self):
        """Start BT discovery (Classic + BLE)."""
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            adapter = dbus.Interface(adapter_obj, self.ADAPTER_IFACE)
            adapter.StartDiscovery()
            return True
        except Exception as e:
            logger.log("ERROR", f"Failed to start BT scan: {e}")
            return False

    def stop_scan(self):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            adapter = dbus.Interface(adapter_obj, self.ADAPTER_IFACE)
            adapter.StopDiscovery()
            return True
        except Exception as e:
            return False

    # ------------------------------------------------------------
    # DEVICE LISTING
    # ------------------------------------------------------------
    def list_devices(self):
        """Return all devices discovered by BlueZ."""
        devices = []
        try:
            manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                "org.freedesktop.DBus.ObjectManager"
            )
            objects = manager.GetManagedObjects()

            for path, interfaces in objects.items():
                if self.DEVICE_IFACE not in interfaces:
                    continue

                dev = interfaces[self.DEVICE_IFACE]
                addr = dev.get("Address")
                name = dev.get("Name", "Unknown")
                paired = bool(dev.get("Paired"))
                connected = bool(dev.get("Connected"))
                rssi = int(dev.get("RSSI", 0)) if "RSSI" in dev else None

                devices.append({
                    "path": path,
                    "mac": addr,
                    "name": name,
                    "paired": paired,
                    "connected": connected,
                    "rssi": rssi
                })

        except Exception as e:
            logger.log("ERROR", f"DBus list devices failed: {e}")

        return devices

    # ------------------------------------------------------------
    # PAIRING
    # ------------------------------------------------------------
    def pair(self, mac):
        try:
            dev_path = self._device_path(mac)
            if not dev_path:
                return False

            dev_obj = self.bus.get_object(self.BLUEZ_SERVICE, dev_path)
            dev_iface = dbus.Interface(dev_obj, "org.bluez.Device1")
            dev_iface.Pair()
            return True
        except Exception as e:
            logger.log("ERROR", f"Pairing failed for {mac}: {e}")
            return False

    def remove(self, mac):
        try:
            adapter_obj = self.bus.get_object(self.BLUEZ_SERVICE, self.adapter)
            adapter = dbus.Interface(adapter_obj, self.ADAPTER_IFACE)

            dev_path = self._device_path(mac)
            if not dev_path:
                return False

            adapter.RemoveDevice(dev_path)
            return True
        except:
            return False

    # ------------------------------------------------------------
    # CONNECT / DISCONNECT
    # ------------------------------------------------------------
    def connect(self, mac):
        try:
            dev_path = self._device_path(mac)
            dev_obj = self.bus.get_object(self.BLUEZ_SERVICE, dev_path)
            dev_iface = dbus.Interface(dev_obj, self.DEVICE_IFACE)
            dev_iface.Connect()
            return True
        except Exception as e:
            logger.log("ERROR", f"Failed to connect {mac}: {e}")
            return False

    def disconnect(self, mac):
        try:
            dev_path = self._device_path(mac)
            dev_obj = self.bus.get_object(self.BLUEZ_SERVICE, dev_path)
            dev_iface = dbus.Interface(dev_obj, self.DEVICE_IFACE)
            dev_iface.Disconnect()
            return True
        except:
            return False

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _device_path(self, mac):
        """Find DBus object path for a MAC."""
        try:
            manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                "org.freedesktop.DBus.ObjectManager"
            )
            objects = manager.GetManagedObjects()

            for path, interfaces in objects.items():
                if self.DEVICE_IFACE not in interfaces:
                    continue
                dev = interfaces[self.DEVICE_IFACE]
                if dev.get("Address") == mac:
                    return path

        except Exception:
            return None

        return None

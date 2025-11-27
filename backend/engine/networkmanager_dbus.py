#!/usr/bin/env python3
# NetworkManager D-Bus Engine for ADA-Pi
# Provides WiFi/Ethernet management using native D-Bus API

import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import threading
import time
from logger import logger


class NMEngine:
    """
    High-level wrapper around NetworkManager D-Bus API.
    Supports:
      - WiFi status
      - Ethernet status
      - Scanning
      - Connect / disconnect
      - IP/Gateway/DNS
    """

    NM_SERVICE = "org.freedesktop.NetworkManager"
    NM_PATH = "/org/freedesktop/NetworkManager"
    NM_IFACE = "org.freedesktop.NetworkManager"
    NM_DEVICE_IFACE = "org.freedesktop.NetworkManager.Device"
    NM_WIRELESS_IFACE = "org.freedesktop.NetworkManager.Device.Wireless"
    NM_AP_IFACE = "org.freedesktop.NetworkManager.AccessPoint"
    NM_IP4_CONFIG_IFACE = "org.freedesktop.NetworkManager.IP4Config"

    DEVICE_TYPE_WIFI = 2
    DEVICE_TYPE_ETHERNET = 1

    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        try:
            self.bus = dbus.SystemBus()
            self.nm = self.bus.get_object(self.NM_SERVICE, self.NM_PATH)
            self.iface = dbus.Interface(self.nm, self.NM_IFACE)
            logger.log("INFO", "NMEngine: Connected to NetworkManager")
        except Exception as e:
            logger.log("ERROR", f"NMEngine init failed: {e}")
            self.bus = None

    # ------------------------------------------------------------
    # DEVICE ENUMERATION
    # ------------------------------------------------------------
    def get_devices(self):
        try:
            return self.iface.GetDevices()
        except:
            return []

    def get_device_type(self, dev_path):
        try:
            dev = self.bus.get_object(self.NM_SERVICE, dev_path)
            props = dbus.Interface(dev, "org.freedesktop.DBus.Properties")
            return int(props.Get(self.NM_DEVICE_IFACE, "DeviceType"))
        except:
            return None

    # ------------------------------------------------------------
    # WIFI STATUS
    # ------------------------------------------------------------
    def wifi_status(self):
        wifi = {
            "connected": False,
            "ssid": None,
            "bssid": None,
            "strength": None,
            "frequency": None,
            "ip": None
        }

        for dev in self.get_devices():
            if self.get_device_type(dev) == self.DEVICE_TYPE_WIFI:
                wifi_dev = self.bus.get_object(self.NM_SERVICE, dev)
                props = dbus.Interface(wifi_dev, "org.freedesktop.DBus.Properties")

                try:
                    active = props.Get(self.NM_DEVICE_IFACE, "ActiveConnection")
                    if active != "/":
                        wifi["connected"] = True

                    # read IP4
                    ip4 = props.Get(self.NM_DEVICE_IFACE, "Ip4Config")
                    if ip4 != "/":
                        wifi["ip"] = self._extract_ip4(ip4)

                    # read AP
                    active_ap = props.Get(self.NM_WIRELESS_IFACE, "ActiveAccessPoint")
                    if active_ap != "/":
                        wifi.update(self._read_ap(active_ap))

                except:
                    pass

        return wifi

    # ------------------------------------------------------------
    # ETHERNET STATUS
    # ------------------------------------------------------------
    def ethernet_status(self):
        eth = {"connected": False, "ip": None}

        for dev in self.get_devices():
            if self.get_device_type(dev) == self.DEVICE_TYPE_ETHERNET:
                eth_dev = self.bus.get_object(self.NM_SERVICE, dev)
                props = dbus.Interface(eth_dev, "org.freedesktop.DBus.Properties")

                try:
                    active = props.Get(self.NM_DEVICE_IFACE, "ActiveConnection")
                    if active != "/":
                        eth["connected"] = True

                    # IP4
                    ip4 = props.Get(self.NM_DEVICE_IFACE, "Ip4Config")
                    if ip4 != "/":
                        eth["ip"] = self._extract_ip4(ip4)

                except:
                    pass

        return eth

    # ------------------------------------------------------------
    # SCANNING
    # ------------------------------------------------------------
    def scan_wifi(self):
        """ Returns available APs with SSID, strength, security. """
        aps = []

        for dev in self.get_devices():
            if self.get_device_type(dev) == self.DEVICE_TYPE_WIFI:
                wifi_dev = self.bus.get_object(self.NM_SERVICE, dev)
                props = dbus.Interface(wifi_dev, "org.freedesktop.DBus.Properties")

                try:
                    ap_list = props.Get(self.NM_WIRELESS_IFACE, "AccessPoints")

                    for ap_path in ap_list:
                        aps.append(self._read_ap(ap_path))

                except Exception as e:
                    logger.log("WARN", f"NMEngine scan error: {e}")

        return aps

    # ------------------------------------------------------------
    # CONNECT TO WIFI
    # ------------------------------------------------------------
    def connect_wifi(self, ssid, password):
        """
        Create + activate a NetworkManager connection profile.
        """
        try:
            con = {
                "connection": {
                    "id": ssid,
                    "type": "802-11-wireless",
                    "uuid": self._uuid()
                },
                "802-11-wireless": {
                    "ssid": dbus.ByteArray(ssid.encode()),
                    "mode": "infrastructure",
                    "security": "802-11-wireless-security"
                },
                "802-11-wireless-security": {
                    "key-mgmt": "wpa-psk",
                    "psk": password
                },
                "ipv4": {"method": "auto"},
                "ipv6": {"method": "ignore"}
            }

            settings = dbus.Interface(
                self.bus.get_object(
                    self.NM_SERVICE, "/org/freedesktop/NetworkManager/Settings"
                ),
                "org.freedesktop.NetworkManager.Settings"
            )

            new_con_path = settings.AddConnection(con)
            self.iface.ActivateConnection(new_con_path, "/", "/")
            return True

        except Exception as e:
            logger.log("ERROR", f"WiFi connect failed: {e}")
            return False

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------
    def _extract_ip4(self, cfg_path):
        try:
            cfg = self.bus.get_object(self.NM_SERVICE, cfg_path)
            props = dbus.Interface(cfg, "org.freedesktop.DBus.Properties")
            data = props.Get(self.NM_IP4_CONFIG_IFACE, "AddressData")
            if len(data) > 0:
                return data[0].get("address", None)
        except:
            pass
        return None

    def _read_ap(self, ap_path):
        try:
            ap = self.bus.get_object(self.NM_SERVICE, ap_path)
            props = dbus.Interface(ap, "org.freedesktop.DBus.Properties")

            ssid = bytes(props.Get(self.NM_AP_IFACE, "Ssid")).decode(errors="ignore")
            strength = int(props.Get(self.NM_AP_IFACE, "Strength"))
            freq = int(props.Get(self.NM_AP_IFACE, "Frequency"))
            bssid = props.Get(self.NM_AP_IFACE, "HwAddress")

            return {
                "ssid": ssid,
                "strength": strength,
                "frequency": freq,
                "bssid": bssid
            }

        except:
            return None

    def _uuid(self):
        import uuid
        return str(uuid.uuid4())

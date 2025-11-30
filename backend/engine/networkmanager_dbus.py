#!/usr/bin/env python3
# Modern NetworkManager engine using dbus-next
# Fully compatible with Python 3.11 and Raspberry Pi OS Bookworm

import asyncio
from dbus_next.aio import MessageBus
from dbus_next import Variant

NM_SERVICE = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
NM_IFACE = "org.freedesktop.NetworkManager"
NM_DEV_IFACE = "org.freedesktop.NetworkManager.Device"
NM_WIRELESS_IFACE = "org.freedesktop.NetworkManager.Device.Wireless"
NM_AP_IFACE = "org.freedesktop.NetworkManager.AccessPoint"
NM_IP4_IFACE = "org.freedesktop.NetworkManager.IP4Config"

DEVICE_TYPE_ETHERNET = 1
DEVICE_TYPE_WIFI = 2


class NMEngine:
    """
    Replacement for the old dbus-python engine.
    Provides:
        - wifi_status()
        - ethernet_status()
        - scan_wifi()
    
    Drops:
        - connect_wifi()
        (can be added later on dbus-next if needed)

    All methods are SYNC wrappers around async dbus-next calls.
    Safe for your existing threaded worker.
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.bus = self.loop.run_until_complete(MessageBus().connect())
            obj = self.loop.run_until_complete(self.bus.introspect(NM_SERVICE, NM_PATH))
            self.nm = self.bus.get_proxy_object(NM_SERVICE, NM_PATH, obj).get_interface(NM_IFACE)
        except Exception as e:
            print(f"[NMEngine] Failed to connect to NetworkManager: {e}")
            self.bus = None

    # ------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------

    def _run(self, coro):
        """Run async tasks synchronously for thread worker usage."""
        return self.loop.run_until_complete(coro)

    async def _get_prop(self, path, iface, prop):
        try:
            obj = await self.bus.introspect(NM_SERVICE, path)
            proxy = self.bus.get_proxy_object(NM_SERVICE, path, obj)
            props = proxy.get_interface("org.freedesktop.DBus.Properties")
            value = await props.call_get(iface, prop)
            return value.value if isinstance(value, Variant) else value
        except:
            return None

    async def _get_devices(self):
        try:
            devices = await self.nm.call_get_devices()
            return devices
        except:
            return []

    # ------------------------------------------------------------
    # DEVICE TYPE CHECK
    # ------------------------------------------------------------

    async def _get_device_type(self, dev):
        return await self._get_prop(dev, NM_DEV_IFACE, "DeviceType")

    async def _get_wifi_device(self):
        for dev in await self._get_devices():
            if await self._get_device_type(dev) == DEVICE_TYPE_WIFI:
                return dev
        return None

    async def _get_eth_device(self):
        for dev in await self._get_devices():
            if await self._get_device_type(dev) == DEVICE_TYPE_ETHERNET:
                return dev
        return None

    # ------------------------------------------------------------
    # WIFI STATUS
    # ------------------------------------------------------------

    def wifi_status(self):
        return self._run(self._wifi_status())

    async def _wifi_status(self):
        wifi = {
            "connected": False,
            "ssid": None,
            "bssid": None,
            "strength": None,
            "frequency": None,
            "ip": None
        }

        dev = await self._get_wifi_device()
        if not dev:
            return wifi

        active = await self._get_prop(dev, NM_DEV_IFACE, "ActiveConnection")
        if active and active != "/":
            wifi["connected"] = True

        ip4 = await self._get_prop(dev, NM_DEV_IFACE, "Ip4Config")
        if ip4 and ip4 != "/":
            wifi["ip"] = await self._extract_ip4(ip4)

        ap_path = await self._get_prop(dev, NM_WIRELESS_IFACE, "ActiveAccessPoint")
        if ap_path and ap_path != "/":
            wifi.update(await self._read_ap(ap_path))

        return wifi

    # ------------------------------------------------------------
    # ETHERNET STATUS
    # ------------------------------------------------------------

    def ethernet_status(self):
        return self._run(self._ethernet_status())

    async def _ethernet_status(self):
        eth = {"connected": False, "ip": None}

        dev = await self._get_eth_device()
        if not dev:
            return eth

        active = await self._get_prop(dev, NM_DEV_IFACE, "ActiveConnection")
        if active and active != "/":
            eth["connected"] = True

        ip4 = await self._get_prop(dev, NM_DEV_IFACE, "Ip4Config")
        if ip4 and ip4 != "/":
            eth["ip"] = await self._extract_ip4(ip4)

        return eth

    # ------------------------------------------------------------
    # SCANNING
    # ------------------------------------------------------------

    def scan_wifi(self):
        return self._run(self._scan_wifi())

    async def _scan_wifi(self):
        dev = await self._get_wifi_device()
        if not dev:
            return []

        obj = await self.bus.introspect(NM_SERVICE, dev)
        proxy = self.bus.get_proxy_object(NM_SERVICE, dev, obj)
        wifi_iface = proxy.get_interface(NM_WIRELESS_IFACE)

        try:
            await wifi_iface.call_request_scan({})
        except:
            pass

        aps = await wifi_iface.call_get_access_points()

        networks = []
        for ap_path in aps:
            info = await self._read_ap(ap_path)
            if info:
                networks.append(info)

        return networks

    # ------------------------------------------------------------
    # AP INFO
    # ------------------------------------------------------------

    async def _read_ap(self, ap_path):
        ssid_bytes = await self._get_prop(ap_path, NM_AP_IFACE, "Ssid")
        if not ssid_bytes:
            return None

        ssid = "".join(chr(b) for b in ssid_bytes)

        return {
            "ssid": ssid,
            "strength": await self._get_prop(ap_path, NM_AP_IFACE, "Strength"),
            "frequency": await self._get_prop(ap_path, NM_AP_IFACE, "Frequency"),
            "bssid": await self._get_prop(ap_path, NM_AP_IFACE, "HwAddress")
        }

    # ------------------------------------------------------------
    # IP4 PARSE
    # ------------------------------------------------------------

    async def _extract_ip4(self, path):
        try:
            obj = await self.bus.introspect(NM_SERVICE, path)
            proxy = self.bus.get_proxy_object(NM_SERVICE, path, obj)
            props = proxy.get_interface("org.freedesktop.DBus.Properties")
            data = await props.call_get(NM_IP4_IFACE, "AddressData")
            if data and len(data.value) > 0:
                return data.value[0].get("address")
        except:
            return None

        return None

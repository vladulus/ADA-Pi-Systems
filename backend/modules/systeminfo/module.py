#!/usr/bin/env python3
# ADA-Pi System Info Module
# Stores system information state

import time


class SystemInfoModule:
    def __init__(self):
        self.cpu_temp = 0.0
        self.gpu_temp = 0.0
        self.cpu_usage = 0.0
        self.ram = {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0
        }
        self.disk = {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0
        }
        self.uptime = 0
        self.load = [0.0, 0.0, 0.0]
        self.os_version = "Unknown"
        self.kernel = "Unknown"
        self.cpu_freq = 0
        self.throttled = False
        self.timestamp = 0

    def update(self, **kwargs):
        """Update system info with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.timestamp = int(time.time())

    def read_status(self):
        """Return JSON-friendly dictionary for API + UI."""
        return {
            "cpu": {
                "temp": self.cpu_temp,
                "usage": self.cpu_usage,
                "freq": self.cpu_freq
            },
            "gpu": {
                "temp": self.gpu_temp
            },
            "memory": self.ram,
            "disk": self.disk,
            "uptime": self.uptime,
            "load": self.load,
            "os_version": self.os_version,
            "kernel": self.kernel,
            "throttled": self.throttled,
            "timestamp": self.timestamp
        }



import time
import os
import psutil
import subprocess
from logger import logger
from ipc.router import router


class SystemInfoWorker:
    INTERVAL = 2  # seconds

    def __init__(self, module):
        self.mod = module
        self.running = True

        logger.log("INFO", "SystemInfoWorker initialized")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "SystemInfoWorker started")

        while self.running:
            try:
                data = {
                    "cpu_temp": self._cpu_temp(),
                    "gpu_temp": self._gpu_temp(),
                    "cpu_usage": psutil.cpu_percent(interval=None),
                    "ram": self._ram(),
                    "disk": self._disk(),
                    "uptime": self._uptime(),
                    "load": os.getloadavg(),
                    "os_version": self._os_version(),
                    "kernel": self._kernel(),
                    "cpu_freq": self._cpu_freq(),
                    "throttled": self._throttled(),
                }

                self.mod.update(**data)

                router.publish("system_update", self.mod.read_status())

                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"SystemInfoWorker crash: {e}")
                time.sleep(2)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # TEMPERATURES
    # ------------------------------------------------------------
    def _cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000.0
        except:
            return 0.0

    def _gpu_temp(self):
        try:
            out = subprocess.check_output(
                ["vcgencmd", "measure_temp"]
            ).decode()
            # output: temp=45.8'C
            return float(out.replace("temp=", "").replace("'C", ""))
        except:
            return 0.0

    # ------------------------------------------------------------
    # CPU FREQUENCY
    # ------------------------------------------------------------
    def _cpu_freq(self):
        try:
            with open("/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq") as f:
                return int(f.read().strip()) // 1000  # convert kHz → MHz
        except:
            return 0

    # ------------------------------------------------------------
    # OS + KERNEL
    # ------------------------------------------------------------
    def _os_version(self):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().replace('"', "")
        except:
            return "Unknown OS"

    def _kernel(self):
        try:
            return os.uname().release
        except:
            return "Unknown Kernel"

    # ------------------------------------------------------------
    # RAM + DISK
    # ------------------------------------------------------------
    def _ram(self):
        m = psutil.virtual_memory()
        return {
            "total": m.total,
            "used": m.used,
            "free": m.available,
            "percent": m.percent
        }

    def _disk(self):
        d = psutil.disk_usage("/")
        return {
            "total": d.total,
            "used": d.used,
            "free": d.free,
            "percent": d.percent
        }

    # ------------------------------------------------------------
    # UPTIME
    # ------------------------------------------------------------
    def _uptime(self):
        try:
            with open("/proc/uptime") as f:
                return int(float(f.read().split()[0]))
        except:
            return 0

    # ------------------------------------------------------------
    # THROTTLED (RASPBERRY PI ONLY)
    # ------------------------------------------------------------
    def _throttled(self):
        """
        Raspberry Pi:
        vcgencmd get_throttled
        Output: throttled=0x0 or flags
        """
        try:
            out = subprocess.check_output(
                ["vcgencmd", "get_throttled"]
            ).decode()
            # "throttled=0x0"
            val = int(out.split("=")[1], 16)
            return val != 0
        except:
            return False
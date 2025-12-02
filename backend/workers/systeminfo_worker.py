import os
import time
from logger import logger
from ipc.router import router


class SystemInfoWorker:
    """
    Worker thread that collects system information:
    - CPU temperature
    - CPU load
    - Memory usage
    - Disk usage
    - Uptime

    Pushes real-time updates to the UI and cloud uploader.
    """

    INTERVAL = 2  # seconds

    def __init__(self, system_module):
        self.system = system_module
        self.running = True

    # ------------------------------------------------------------

    def start(self):
        logger.log("INFO", "SystemInfoWorker started.")

        while self.running:
            try:
                self.update_system_info()
                time.sleep(self.INTERVAL)
            except Exception as e:
                logger.log("ERROR", f"SystemInfoWorker crashed: {e}")
                time.sleep(1)

    # ------------------------------------------------------------

    def stop(self):
        self.running = False

    # ------------------------------------------------------------

    def update_system_info(self):
        """
        Read all system info fields and update module + publish UI event.
        """

        cpu_temp = self.get_cpu_temp()
        cpu_usage = self.get_cpu_load()
        mem_info = self.get_mem_usage()
        disk_info = self.get_disk_usage()

        payload = {
            "cpu_temp": cpu_temp,
            "cpu_usage": cpu_usage,
            "ram": mem_info,
            "disk": disk_info,
            "uptime": self.get_uptime(),
            "load": os.getloadavg(),
        }

        # Update module with explicit fields
        self.system.update(**payload)

        # Push WebSocket event with normalized structure
        router.publish("system_update", self.system.read_status())

    # ------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------

    def get_cpu_temp(self):
        """
        Raspberry Pi CPU temperature.
        Works on Pi 4/5 (thermal_zone0).
        """

        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return round(int(f.read()) / 1000, 1)
        except:
            return 0.0

    # ------------------------------------------------------------

    def get_cpu_load(self):
        """Returns CPU load percentage (0-100)."""

        try:
            load1, _, _ = os.getloadavg()
            cores = max(1, os.cpu_count() or 1)
            return round((load1 / cores) * 100, 1)
        except Exception:
            return 0.0

    # ------------------------------------------------------------

    def get_mem_usage(self):
        """Read memory usage from /proc/meminfo."""

        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    key, value, _ = line.split()
                    info[key] = int(value)

            total = info.get("MemTotal", 0) // 1024
            free = info.get("MemAvailable", 0) // 1024
            used = total - free
            percent = round((used / total) * 100, 1) if total else 0.0

            return {
                "total": total,
                "used": used,
                "free": free,
                "percent": percent,
            }

        except Exception:
            return {"total": 0, "used": 0, "free": 0, "percent": 0.0}

    # ------------------------------------------------------------

    def get_uptime(self):
        """Return uptime in seconds."""

        try:
            with open("/proc/uptime") as f:
                return int(float(f.read().split()[0]))
        except Exception:
            return 0

    # ------------------------------------------------------------

    def get_disk_usage(self):
        """Return total/used disk space (MB) for root filesystem."""

        try:
            st = os.statvfs("/")
            total = (st.f_blocks * st.f_frsize) // (1024 * 1024)
            free = (st.f_bavail * st.f_frsize) // (1024 * 1024)
            used = total - free
            percent = round((used / total) * 100, 1) if total else 0.0
            return {"total": total, "used": used, "free": free, "percent": percent}
        except Exception:
            return {"total": 0, "used": 0, "free": 0, "percent": 0.0}

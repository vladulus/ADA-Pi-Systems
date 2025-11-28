import time
import os
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

    def __init__(self, modules):
        self.modules = modules
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
        cpu_load = self.get_cpu_load()
        mem_info = self.get_mem_usage()
        uptime = self.get_uptime()
        disk_info = self.get_disk_usage()

        payload = {
            "cpu_temp": cpu_temp,
            "cpu_load": cpu_load,
            "mem_used": mem_info["used"],
            "mem_total": mem_info["total"],
            "disk_used": disk_info["used"],
            "disk_total": disk_info["total"],
            "uptime": uptime
        }

        # Update module - FIX: Use dot notation instead of subscript
        self.modules.system.update(payload)

        # Push WebSocket event
        router.publish("system_update", payload)

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
        """
        Returns CPU load percentage (0-100).
        """

        try:
            load1, load5, load15 = os.getloadavg()
            cores = os.cpu_count()
            return round((load1 / cores) * 100, 1)
        except:
            return 0.0

    # ------------------------------------------------------------

    def get_mem_usage(self):
        """
        Read memory usage from /proc/meminfo.
        """

        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    key, value, _ = line.split()
                    info[key] = int(value)

            total = info.get("MemTotal", 0) // 1024
            free = info.get("MemAvailable", 0) // 1024
            used = total - free

            return {"total": total, "used": used}

        except:
            return {"total": 0, "used": 0}

    # ------------------------------------------------------------

    def get_uptime(self):
        """
        Return uptime in seconds.
        """

        try:
            with open("/proc/uptime") as f:
                return int(float(f.read().split()[0]))
        except:
            return 0

    # ------------------------------------------------------------

    def get_disk_usage(self):
        """
        Return total/used disk space (MB) for root filesystem.
        """

        try:
            st = os.statvfs("/")
            total = (st.f_blocks * st.f_frsize) // (1024 * 1024)
            free = (st.f_bavail * st.f_frsize) // (1024 * 1024)
            used = total - free
            return {"total": total, "used": used}
        except:
            return {"total": 0, "used": 0}

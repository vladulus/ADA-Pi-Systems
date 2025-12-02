#!/usr/bin/env python3
# ADA-Pi UPS Worker with X1202 + Generic support

import importlib
import importlib.util
import time
import os
import subprocess


def _load_smbus_module():
    """Return the first available SMBus-compatible module (smbus2 preferred)."""
    for name in ("smbus2", "smbus"):
        if importlib.util.find_spec(name) is not None:
            module = importlib.import_module(name)
            return module, name
    return None, None


SMBUS_MODULE, SMBUS_MODULE_NAME = _load_smbus_module()
from logger import logger
from ipc.router import router
from config_manager import load_config


class UPSWorker:
    """
    Supports:
      ✔ Geekworm X1202 UPS (I2C)
      ✔ Generic voltage-based UPS

    Features:
      ✔ Auto-enable I2C
      ✔ Read voltage
      ✔ Calculate percent
      ✔ Detect charging state
      ✔ Detect input power state
      ✔ Configurable shutdown threshold
      ✔ Soft-shutdown for X1202
    """

    INTERVAL = 2  # seconds
    X1202_I2C_ADDR = 0x36
    X1202_REG_VCELL = 0x02
    X1202_REG_SOC   = 0x04
    X1202_REG_MODE  = 0x06

    def __init__(self, ups_module):
        self.ups = ups_module
        self.running = True
        self.bus = None

        # load & cache config
        cfg = load_config()
        self.shutdown_pct = cfg.get("ups_shutdown_pct", 10)
        self.model = cfg.get("ups_model", "auto").lower()

        # normalize aliases so users can specify "x102" or "x1002" for the Geekworm board
        if self.model in ("x102", "x1002"):
            self.model = "x1202"

        self._init_i2c()
        self._detect_model()

    # ------------------------------------------------------------
    # INIT FUNCTIONS
    # ------------------------------------------------------------
    def _init_i2c(self):
        """Enable the I²C interface if not already enabled."""
        # Skip I²C setup entirely when the UPS is explicitly configured as generic
        # to avoid unnecessary dependency warnings for USB-only setups.
        if self.model == "generic":
            self.bus = None
            return

        if SMBUS_MODULE is None:
            logger.log("WARN", "No SMBus module (smbus2/smbus) available; skipping I2C initialization. UPSWorker will run in generic mode.")
            self.bus = None
            return

        try:
            if not os.path.exists("/dev/i2c-1"):
                logger.log("INFO", "Enabling I2C interface via raspi-config...")
                subprocess.run(
                    ["sudo", "raspi-config", "nonint", "do_i2c", "0"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                time.sleep(1)

            self.bus = SMBUS_MODULE.SMBus(1)
            logger.log("INFO", f"I2C bus initialized using {SMBUS_MODULE_NAME}.")
        except Exception as e:
            logger.log("ERROR", f"Failed to init I2C: {e}")
            self.bus = None

    # ------------------------------------------------------------
    def _detect_model(self):
        """Auto-detect if X1202 is present."""
        if self.model != "auto":
            self.ups.update(model=self.model)
            return

        try:
            if self.bus:
                self.bus.read_byte_data(self.X1202_I2C_ADDR, self.X1202_REG_SOC)
                self.model = "x1202"
                logger.log("INFO", "Geekworm X1202 UPS detected.")
                self.ups.update(model="x1202")
                return
        except:
            pass

        # fallback
        self.model = "generic"
        logger.log("INFO", "Falling back to generic UPS mode.")
        self.ups.update(model="generic")

    # ------------------------------------------------------------
    # WORKER
    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "UPSWorker started.")

        while self.running:
            try:
                if self.model == "x1202":
                    self._read_x1202()
                else:
                    self._read_generic()

                self._check_shutdown()

                router.publish("ups_update", self.ups.read_status())

                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"UPSWorker crash: {e}")
                time.sleep(2)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # X1202 UPS READING
    # ------------------------------------------------------------
    def _read_x1202(self):
        try:
            if not self.bus:
                raise RuntimeError("I2C bus unavailable")

            # voltage register (12-bit)
            vcell = self.bus.read_word_data(self.X1202_I2C_ADDR, self.X1202_REG_VCELL)
            vcell = ((vcell & 0xFF) << 8) | (vcell >> 8)
            voltage = (vcell >> 4) * 1.25 / 1000.0  # conversion from datasheet

            # % battery
            soc = self.bus.read_byte_data(self.X1202_I2C_ADDR, self.X1202_REG_SOC)

            # detect charging
            charging = soc > self.ups.read_status()["percent"]

            # detect input power:
            # X1202 does not expose this directly → infer from voltage increase
            input_power = charging

            self.ups.update(
                voltage=round(voltage, 3),
                percent=int(soc),
                charging=charging,
                input_power=input_power
            )

        except Exception as e:
            logger.log("WARN", f"X1202 read failed, switching to generic: {e}")
            self.model = "generic"

    # ------------------------------------------------------------
    # GENERIC UPS READING (fallback)
    # ------------------------------------------------------------
    def _read_generic(self):
        """
        Assumes ADC or USB UPS that provides 5V/charging voltage.
        Very basic fallback.
        """
        try:
            # read system voltage from Raspberry Pi
            with open("/sys/class/power_supply/usb-pd0/voltage_now") as f:
                raw = int(f.read().strip())
                voltage = raw / 1_000_000.0

        except:
            voltage = 5.0

        percent = max(0, min(100, int((voltage - 3.3) / (4.2 - 3.3) * 100)))

        charging = voltage > 4.9

        self.ups.update(
            voltage=round(voltage, 3),
            percent=percent,
            charging=charging,
            input_power=charging
        )

    # ------------------------------------------------------------
    # AUTO-SHUTDOWN MANAGEMENT
    # ------------------------------------------------------------
    def _check_shutdown(self):
        status = self.ups.read_status()

        if status["percent"] <= self.shutdown_pct and not status["charging"]:
            logger.log("WARN", f"Battery low ({status['percent']}%) – initiating shutdown!")
            os.system("sudo shutdown -h now")

#!/usr/bin/env python3
# ADA-Pi UPS Worker
# Supports:
#   ✔ Geekworm X1202 (I2C 0x36)
#   ✔ WittyPi 4 L3V7 (I2C 0x08)
#   ✔ Generic fallback

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
    UPS Worker with multi-device support.
    
    Supports:
      ✔ Geekworm X1202 UPS (I2C 0x36)
      ✔ WittyPi 4 L3V7 (I2C 0x08)
      ✔ Generic voltage-based UPS
    """

    INTERVAL = 2  # seconds
    
    # X1202 I2C registers
    X1202_I2C_ADDR = 0x36
    X1202_REG_VCELL = 0x02
    X1202_REG_SOC = 0x04
    X1202_REG_MODE = 0x06
    
    # WittyPi 4 L3V7 I2C registers
    WITTYPI_I2C_ADDR = 0x08
    WITTYPI_REG_VIN_INT = 0x01      # Input voltage integer part
    WITTYPI_REG_VIN_DEC = 0x02      # Input voltage decimal (x100)
    WITTYPI_REG_VOUT_INT = 0x03     # Output voltage integer part
    WITTYPI_REG_VOUT_DEC = 0x04     # Output voltage decimal (x100)
    WITTYPI_REG_IOUT_INT = 0x05     # Output current integer part
    WITTYPI_REG_IOUT_DEC = 0x06     # Output current decimal (x100)
    WITTYPI_REG_POWER_MODE = 0x07   # 1=battery, 0=USB 5V
    WITTYPI_REG_LV_SHUTDOWN = 0x08  # Low voltage shutdown flag
    WITTYPI_REG_TEMP = 0x32         # Temperature register (mapped from LM75B)

    def __init__(self, ups_module):
        self.ups = ups_module
        self.running = True
        self.bus = None
        self.last_percent = 0

        # Load config
        cfg = load_config()
        ups_cfg = cfg.get("ups", {})
        
        self.shutdown_pct = ups_cfg.get("shutdown_pct", 10)
        self.model = ups_cfg.get("type", "auto").lower()
        
        # Normalize aliases
        if self.model in ("x102", "x1002"):
            self.model = "x1202"
        if self.model in ("witty", "wittypi4", "wittypi4l3v7"):
            self.model = "wittypi"

        self._init_i2c()
        self._detect_model()

    # ----------------------------------------------------------------
    # INIT
    # ----------------------------------------------------------------
    def _init_i2c(self):
        """Enable the I²C interface."""
        if self.model == "generic" or self.model == "none":
            self.bus = None
            return

        if SMBUS_MODULE is None:
            logger.log("WARN", "No SMBus module available; UPS in generic mode.")
            self.bus = None
            return

        try:
            if not os.path.exists("/dev/i2c-1"):
                logger.log("INFO", "Enabling I2C via raspi-config...")
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

    def _detect_model(self):
        """Auto-detect UPS model if set to 'auto'."""
        if self.model != "auto":
            self.ups.update(model=self.model)
            logger.log("INFO", f"UPS model configured: {self.model}")
            return

        if not self.bus:
            self.model = "generic"
            self.ups.update(model="generic")
            return

        # Try X1202 first (0x36)
        try:
            self.bus.read_byte_data(self.X1202_I2C_ADDR, self.X1202_REG_SOC)
            self.model = "x1202"
            logger.log("INFO", "Geekworm X1202 UPS detected.")
            self.ups.update(model="x1202")
            return
        except:
            pass

        # Try WittyPi (0x08)
        try:
            self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_VIN_INT)
            self.model = "wittypi"
            logger.log("INFO", "WittyPi 4 L3V7 UPS detected.")
            self.ups.update(model="wittypi")
            return
        except:
            pass

        # Fallback
        self.model = "generic"
        logger.log("INFO", "No UPS detected, falling back to generic mode.")
        self.ups.update(model="generic")

    # ----------------------------------------------------------------
    # WORKER
    # ----------------------------------------------------------------
    def start(self):
        logger.log("INFO", f"UPSWorker started (model={self.model}).")

        while self.running:
            try:
                if self.model == "x1202":
                    self._read_x1202()
                elif self.model == "wittypi":
                    self._read_wittypi()
                else:
                    self._read_generic()

                self._check_shutdown()

                router.publish("ups_update", self.ups.read_status())

                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"UPSWorker crash: {e}")
                time.sleep(2)

    def stop(self):
        self.running = False

    # ----------------------------------------------------------------
    # X1202 UPS
    # ----------------------------------------------------------------
    def _read_x1202(self):
        try:
            if not self.bus:
                raise RuntimeError("I2C bus unavailable")

            # Voltage register (12-bit)
            vcell = self.bus.read_word_data(self.X1202_I2C_ADDR, self.X1202_REG_VCELL)
            vcell = ((vcell & 0xFF) << 8) | (vcell >> 8)
            voltage = (vcell >> 4) * 1.25 / 1000.0

            # Battery percentage
            soc = self.bus.read_byte_data(self.X1202_I2C_ADDR, self.X1202_REG_SOC)

            # Detect charging
            charging = soc > self.last_percent
            self.last_percent = soc

            # Input power (inferred)
            input_power = charging

            self.ups.update(
                voltage=round(voltage, 3),
                percent=int(soc),
                charging=charging,
                input_power=input_power
            )

        except Exception as e:
            logger.log("WARN", f"X1202 read failed: {e}")
            self.model = "generic"

    # ----------------------------------------------------------------
    # WITTYPI 4 L3V7
    # ----------------------------------------------------------------
    def _read_wittypi(self):
        """Read UPS data from WittyPi 4 L3V7."""
        try:
            if not self.bus:
                raise RuntimeError("I2C bus unavailable")

            # Read input voltage (Vin)
            vin_int = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_VIN_INT)
            vin_dec = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_VIN_DEC)
            voltage_in = vin_int + (vin_dec / 100.0)

            # Read output voltage (Vout)
            vout_int = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_VOUT_INT)
            vout_dec = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_VOUT_DEC)
            voltage_out = vout_int + (vout_dec / 100.0)

            # Read output current (Iout)
            iout_int = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_IOUT_INT)
            iout_dec = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_IOUT_DEC)
            current_out = iout_int + (iout_dec / 100.0)

            # Read power mode (1=battery, 0=USB)
            power_mode = self.bus.read_byte_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_POWER_MODE)
            on_battery = (power_mode == 1)
            input_power = not on_battery

            # Calculate battery percentage from Vin
            # Li-ion: 3.0V = 0%, 4.2V = 100%
            # When on USB power, Vin will be ~5V, so we cap it
            if on_battery:
                percent = self._voltage_to_percent(voltage_in, 3.0, 4.2)
            else:
                # On USB power, battery is charging
                percent = min(100, self._voltage_to_percent(voltage_in, 3.0, 4.2))

            # Detect charging
            charging = input_power and percent < 100

            # Read temperature (optional, mapped from LM75B at register 0x32)
            temperature = None
            try:
                temp_raw = self.bus.read_word_data(self.WITTYPI_I2C_ADDR, self.WITTYPI_REG_TEMP)
                # LM75B format: 11-bit, MSB first
                temp_raw = ((temp_raw & 0xFF) << 8) | (temp_raw >> 8)
                temperature = (temp_raw >> 5) * 0.125
                if temp_raw & 0x8000:  # Negative
                    temperature -= 256
            except:
                pass

            self.last_percent = percent

            self.ups.update(
                model="wittypi",
                voltage=round(voltage_in, 3),
                voltage_out=round(voltage_out, 3),
                current=round(current_out, 3),
                percent=int(percent),
                charging=charging,
                input_power=input_power,
                on_battery=on_battery,
                temperature=temperature
            )

            logger.log("DEBUG", f"WittyPi: Vin={voltage_in:.2f}V, Vout={voltage_out:.2f}V, "
                                f"Iout={current_out:.2f}A, {percent}%, charging={charging}")

        except Exception as e:
            logger.log("WARN", f"WittyPi read failed: {e}")
            # Don't switch to generic immediately, retry
            self.ups.update(error=str(e))

    def _voltage_to_percent(self, voltage, v_min, v_max):
        """Convert voltage to percentage."""
        if voltage <= v_min:
            return 0
        if voltage >= v_max:
            return 100
        return int((voltage - v_min) / (v_max - v_min) * 100)

    # ----------------------------------------------------------------
    # GENERIC UPS
    # ----------------------------------------------------------------
    def _read_generic(self):
        """Generic fallback using system voltage."""
        try:
            with open("/sys/class/power_supply/usb-pd0/voltage_now") as f:
                raw = int(f.read().strip())
                voltage = raw / 1_000_000.0
        except:
            voltage = 5.0

        percent = self._voltage_to_percent(voltage, 3.3, 4.2)
        charging = voltage > 4.9

        self.ups.update(
            voltage=round(voltage, 3),
            percent=percent,
            charging=charging,
            input_power=charging
        )

    # ----------------------------------------------------------------
    # SHUTDOWN CHECK
    # ----------------------------------------------------------------
    def _check_shutdown(self):
        """Shutdown if battery is critically low."""
        status = self.ups.read_status()
        percent = status.get("percent", 100)
        charging = status.get("charging", False)

        if percent <= self.shutdown_pct and not charging:
            logger.log("WARN", f"Battery low ({percent}%) – initiating shutdown!")
            os.system("sudo shutdown -h now")

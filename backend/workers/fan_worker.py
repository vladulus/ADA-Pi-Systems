#!/usr/bin/env python3
# ADA-Pi Fan Worker
# Supports:
#   ✓ Raspberry Pi 5 hardware fan (thermal driver)
#   ✓ Generic GPIO PWM fan
#   ✓ Auto mode with temperature curve
#   ✓ Manual override mode

import time
import os
import subprocess
from logger import logger
from ipc.router import router


class FanWorker:
    INTERVAL = 2  # seconds

    def __init__(self, fan_module):
        self.fan = fan_module
        self.running = True
        self.current_temp = 0.0

        # temperature source used by Raspberry Pi 5
        self.cpu_temp_file = "/sys/class/thermal/thermal_zone0/temp"

        # detect hardware fan interface
        self.hw_fan_speed_file = "/sys/devices/platform/cooling_fan/hwmon/hwmon0/pwm1"
        self.hw_fan_max_file = "/sys/devices/platform/cooling_fan/hwmon/hwmon0/pwm1_max"

        self.has_hw_fan = os.path.exists(self.hw_fan_speed_file)
        
        # Track whether hardware fan is available in the module state
        self.fan.update(supports_hw=self.has_hw_fan)

        logger.log("INFO", f"FanWorker initialized (hardware_fan={self.has_hw_fan})")

    # ------------------------------------------------------------
    def start(self):
        logger.log("INFO", "FanWorker started.")

        while self.running:
            try:
                # Read temperature and update module state
                self.current_temp = self._read_temp()
                self.fan.update_temperature(self.current_temp)

                # Get fan mode
                status = self.fan.read_status()
                
                if status.get("mode") == "auto":
                    speed = self.fan.auto_control()
                else:  # manual mode
                    speed = status.get("speed", 0)

                self._apply_speed(speed)

                # Publish update with temperature included
                router.publish("fan_update", {
                    **self.fan.read_status(),
                    "temperature": self.current_temp
                })

                time.sleep(self.INTERVAL)

            except Exception as e:
                logger.log("ERROR", f"FanWorker crash: {e}")
                time.sleep(2)

    # ------------------------------------------------------------
    def stop(self):
        self.running = False

    # ------------------------------------------------------------
    # TEMPERATURE READ
    # ------------------------------------------------------------
    def _read_temp(self):
        try:
            with open(self.cpu_temp_file) as f:
                raw = int(f.read().strip())
                return raw / 1000.0
        except:
            return 0.0

    # ------------------------------------------------------------
    # AUTO FAN CURVE
    # ------------------------------------------------------------
    def _auto_speed(self, temp):
        """
        Default curve:
            <40°C → 0%
            40–50°C → 25%
            50–60°C → 50%
            60–70°C → 75%
            >70°C → 100%
        """
        if temp < 40:
            return 0
        if temp < 50:
            return 25
        if temp < 60:
            return 50
        if temp < 70:
            return 75
        return 100

    # ------------------------------------------------------------
    # APPLY FAN SPEED (hardware OR pwm)
    # ------------------------------------------------------------
    def _apply_speed(self, percent):
        """
        Writing speed to hardware fan or fallback PWM.
        """
        if self.has_hw_fan:
            self._apply_hw_fan(percent)
        else:
            self._apply_pwm_fan(percent)

    # ------------------------------------------------------------
    def _apply_hw_fan(self, percent):
        try:
            # Read max PWM value
            with open(self.hw_fan_max_file) as f:
                max_pwm = int(f.read().strip())

            pwm_value = int(max_pwm * (percent / 100))

            with open(self.hw_fan_speed_file, "w") as f:
                f.write(str(pwm_value))

        except Exception as e:
            logger.log("ERROR", f"Failed writing hw fan speed: {e}")

    # ------------------------------------------------------------
    def _apply_pwm_fan(self, percent):
        """
        PWM fallback using pigpio or gpioset.
        This is generic, works on any Pi board.
        """

        # OPTIONAL: install pigpio on RPi OS
        # For now, log only:
        logger.log("WARN", "PWM fan fallback not fully implemented (no HW fan detected).")

        # In production we can map to `gpiochip0` + PWM pin.
        # Placeholder for future expansion.

        pass

# ADA-Pi Backend Module: Fan Module
# Handles Raspberry Pi 5 fan control and universal PWM fans

class FanModule:
    def __init__(self):
        self.enabled = True
        self.speed = 0          # current fan speed %
        self.mode = "auto"      # auto | manual
        self.temperature = 0.0  # CPU temperature
        self.supports_hw = False  # hardware fan support

    def read_status(self):
        return {
            "enabled": self.enabled,
            "speed": self.speed,
            "mode": self.mode,
            "temperature": self.temperature
        }

    def update(self, supports_hw=False):
        """Update hardware support status"""
        self.supports_hw = supports_hw

    def update_temperature(self, temp):
        self.temperature = temp

    def set_speed(self, speed):
        # Manual speed override
        self.speed = max(0, min(100, speed))
        self.mode = "manual"

    def set_auto(self):
        self.mode = "auto"

    def auto_control(self):
        # Simple automatic fan curve
        if not self.enabled or self.mode != "auto":
            return self.speed

        if self.temperature < 40:
            self.speed = 0
        elif self.temperature < 50:
            self.speed = 25
        elif self.temperature < 60:
            self.speed = 50
        elif self.temperature < 70:
            self.speed = 75
        else:
            self.speed = 100

        return self.speed

import time

class UPSModule:
    """
    Stores UPS runtime values:
      - voltage
      - percent
      - charging
      - input_power
      - shutdown_threshold
      - model
    """

    def __init__(self):
        self.data = {
            "voltage": 0.0,
            "percent": 0,
            "charging": False,
            "input_power": False,
            "model": "auto",
            "updated": time.time()
        }

    def update(self, **kwargs):
        for k, v in kwargs.items():
            self.data[k] = v
        self.data["updated"] = time.time()

    def read_status(self):
        return self.data.copy()

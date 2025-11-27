# ADA-Pi Backend IPC Router
# Central messaging hub between backend modules and UI

class IPCRouter:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_name, callback):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    def publish(self, event_name, data=None):
        # Publish to exact match subscribers
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"IPC callback error: {e}")
        
        # Publish to wildcard subscribers
        if "*" in self.subscribers:
            for callback in self.subscribers["*"]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"IPC wildcard callback error: {e}")

# Global instance
router = IPCRouter()
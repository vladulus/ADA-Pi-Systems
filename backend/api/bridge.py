import asyncio
from ipc.router import router
from logger import logger


class WebSocketBridge:
    """
    Bridges IPC events to WebSocket clients.
    """
    
    def __init__(self, ws_server):
        self.ws = ws_server
        # Subscribe to all backend events
        router.subscribe("*", self.forward_any_event)
    
    # ------------------------------------------------------------
    def forward_any_event(self, data):
        """
        Called whenever ANY router.publish(event, data) is used.
        Forwards the event to all connected WebSocket clients.
        """
        event_name = data.get("__event__")
        if not event_name:
            return
        
        # Check if WebSocket loop is ready
        if not self.ws.loop or not self.ws.loop.is_running():
            return
        
        # Forward to WebSocket in its event loop
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.broadcast(event_name, data),
                self.ws.loop
            )
        except Exception as e:
            logger.log("WARN", f"WebSocket broadcast failed: {e}")
    
    # ------------------------------------------------------------
    @staticmethod
    def enable_event_tracking():
        """
        Modifies router.publish so that every event gets "__event__" key.
        This allows the bridge to know which event type was published.
        """
        original_publish = router.publish
        
        def wrapped(event, payload=None):
            if payload is None:
                payload = {}
            payload["__event__"] = event
            original_publish(event, payload)
        
        router.publish = wrapped

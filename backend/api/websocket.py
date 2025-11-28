#!/usr/bin/env python3
# ADA-Pi WebSocket Server
# Broadcasts IPC events to all connected UI clients

import asyncio
import json
import websockets
from logger import logger


class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.server = None

    # ------------------------------------------------------------
    async def handler(self, websocket, path):
        """Handle new WebSocket client connection"""
        # new client connected
        self.clients.add(websocket)
        logger.log("INFO", f"WebSocket client connected. {len(self.clients)} total")

        try:
            async for message in websocket:
                # client sent a message (for future commands)
                pass
        except Exception as e:
            logger.log("WARN", f"WebSocket client disconnected: {e}")
        finally:
            self.clients.discard(websocket)

    # ------------------------------------------------------------
    async def broadcast(self, event, payload):
        """
        Broadcast message to all connected clients.
        """
        if not self.clients:
            return

        msg = json.dumps({
            "event": event,
            "payload": payload
        })

        # Use websockets.broadcast() for efficient broadcasting
        dead = set()
        for ws in self.clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)

        # Remove dead connections
        self.clients -= dead

    # ------------------------------------------------------------
    def start(self):
        """
        Run WebSocket server in its own thread using a new asyncio loop.
        """
        logger.log("INFO", f"Starting WebSocket server on ws://{self.host}:{self.port}")

        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Start the server
        try:
            start_server = websockets.serve(
                self.handler,
                self.host,
                self.port,
                loop=self.loop
            )
            self.server = self.loop.run_until_complete(start_server)
            logger.log("INFO", f"WebSocket server running on port {self.port}")

            # Run event loop forever
            self.loop.run_forever()
        except Exception as e:
            logger.log("ERROR", f"WebSocket server failed to start: {e}")
        finally:
            if self.server:
                self.server.close()
                self.loop.run_until_complete(self.server.wait_closed())
            self.loop.close()

    # ------------------------------------------------------------
    def stop(self):
        """Stop the WebSocket server"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
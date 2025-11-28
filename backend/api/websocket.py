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
    async def handler(self, websocket):
        """Handle new WebSocket client connection"""
        # new client connected
        self.clients.add(websocket)
        logger.log("INFO", f"WebSocket client connected. {len(self.clients)} total")

        try:
            async for message in websocket:
                # client sent a message (for future commands)
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.log("WARN", f"WebSocket client error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.log("INFO", f"WebSocket client disconnected. {len(self.clients)} remaining")

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

        # Send to all clients
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
            # Run the server - websockets 15.x uses async context manager
            self.loop.run_until_complete(self._run_server())
        except Exception as e:
            logger.log("ERROR", f"WebSocket server failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.loop.close()

    # ------------------------------------------------------------
    async def _run_server(self):
        """Internal async method to run the WebSocket server"""
        try:
            async with websockets.serve(self.handler, self.host, self.port):
                logger.log("INFO", f"WebSocket server running on port {self.port}")
                # Keep server running forever
                await asyncio.Future()  # This never completes
        except Exception as e:
            logger.log("ERROR", f"WebSocket server error: {e}")
            raise

    # ------------------------------------------------------------
    def stop(self):
        """Stop the WebSocket server"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
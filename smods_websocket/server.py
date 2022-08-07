import asyncio
import json
import logging
from multiprocessing import Process

import websockets

from smods_websocket.model import WebsocketMessage
from utils.logger import get_logger

logger = get_logger(__name__)

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
)


class LoggerAdapter(logging.LoggerAdapter):
    """Add connection ID and client IP address to websockets logs."""
    def process(self, msg, kwargs):
        try:
            websocket = kwargs["extra"]["websocket"]
        except KeyError:
            return msg, kwargs
        xff = websocket.request_headers.get("X-Forwarded-For")
        return f"{websocket.id} {xff} {msg}", kwargs


class WsServer(Process):
    def __init__(self, address, port, stop_event):
        super().__init__()
        self.address = address
        self.port = port

        self.stop_event = stop_event
        self.loop = asyncio.get_event_loop()

        self.connections = set()

    async def register(self, websocket):
        self.connections.add(websocket)

    async def unregister(self, websocket):
        self.connections.remove(websocket)

    async def notify(self, message: WebsocketMessage, websocket):
        connection_list = []
        for connection in self.connections:
            if connection != websocket:
                connection_list.append(connection)

        for connection in connection_list:
            await connection.send(message)

    async def handle_connection(self, websocket):
        logger.debug("New connection!")
        await self.register(websocket)
        try:
            await websocket.send(json.dumps({"status": "Connected"}))
            async for message in websocket:
                logger.debug(message)
                await self.notify(message, websocket)
        finally:
            await self.unregister(websocket)

    # async def start_server(self, stop):
    #     async with websockets.serve(self.handle_connection, self.address, self.port,
    #                                 logger=LoggerAdapter(logging.getLogger("websockets.server"), None)):
    #         await stop  # wait for a sto event from the handler

    def run(self) -> None:
        logger.info(f"Starting websocket on port {self.port}")
        # stop = self.loop.run_in_executor(None, self.stop_event.wait)
        # self.loop.run_until_complete(self.start_server(stop))
        ws_server = websockets.serve(self.handle_connection, self.address, self.port,
                                     logger=LoggerAdapter(logging.getLogger("websockets.server"), None))

        self.loop.run_until_complete(ws_server)
        self.loop.run_forever()



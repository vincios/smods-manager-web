import os.path
import threading
import time

import smods_manager.app
from smods_manager import create_app
from smods_websocket.server import WsServer

import multiprocessing

from utils.logger import get_logger

logger = get_logger(__name__)


def start_flask_app():
    logger.info("Starting Flask server...")
    app = create_app()
    app.run()


# def start_websocket(port, stop_handler):
#     logger.info("Starting Websocket server...")
#     start_server(smods_manager.app.WEBSOCKET_PORT, stop_handler)


def start_loop(loop, server):
    loop.run_until_complete(server)
    loop.run_forever()


if __name__ == '__main__':
    logger.info("Starting...")
    logger.info("Checking app folders...")
    smods_manager.app.generate_app_folders()

    logger.info("Checking database...")
    if not os.path.exists(smods_manager.app.db_path):
        logger.info("Database initialization")
        smods_manager.app.init_database()

    logger.info("Starting processes...")
    p_flask = multiprocessing.Process(target=start_flask_app)
    # p_ws = multiprocessing.Process(target=start_websocket, args=(stop,))

    stop_event = threading.Event()

    ws = WsServer("localhost", 5001, stop_event)

    p_flask.start()
    ws.run()

    # p_ws.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Closing processes...")
        stop_event.set()
        p_flask.terminate()
        ws.terminate()

        # p_ws.join()
        p_flask.join()

        logger.info("Processes stopped")

import os
import sqlite3
import threading
import time

import dataBaseOperations
import utils

import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s',
                              '%m-%d-%Y %H:%M:%S')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
def check_shutdown():
    while True:
        if dataBaseOperations.checkForKey("meta", "doAction", "shutdown"):
            utils.doShutdownRoutine(logger)
            break
        time.sleep(5)

def main():
    thread = threading.Thread(target=check_shutdown)
    thread.start()

if __name__ == '__main__':
    logger.info('Starting')
    main()

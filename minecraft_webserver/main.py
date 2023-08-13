import os
import sqlite3
import threading
import time
from flask import Flask, render_template
import dataBaseOperations
import utils

import logging
import sys

# ################################Basic Logging settings###############################################
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%m-%d-%Y %H:%M:%S')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
# #####################################Flask setup#################################################
app = Flask(__name__)
logger.info('Starting')


# ######################################Flask routes################################################
@app.route('/')
def index_route():
    return render_template("index.html")


@app.route('/spieler')
def spieler_overview_route():
    return render_template("spieler.html")


def check_shutdown():
    while True:
        if dataBaseOperations.checkForKey("meta", "doAction", "shutdown"):
            utils.doShutdownRoutine(logger)
            break
        time.sleep(5)


if __name__ == '__main__':
    thread = threading.Thread(target=check_shutdown)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True)

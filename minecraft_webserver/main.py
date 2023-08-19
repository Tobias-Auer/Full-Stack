import logging
import sys
import threading
import time

from flask import Flask, render_template, request

import dataBaseOperations
import utils

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
# #####################################Class Setups################################################
minecraftApi = utils.MinecraftApi(logger=logger)
databasApi = utils.DatabaseApi(logger=logger)
backupApi = utils.BackupApi(logger=logger)
mixedApi = utils.MixedUtilsApi(logger=logger)
# #####################################Flask setup#################################################
app = Flask(__name__)
logger.info('Starting')


# ######################################Flask routes################################################
@app.route('/')
def index_route():
    return render_template("index.html")


@app.route('/spieler')
def player_overview_route():
    status = "Offline"  # Todo: Get correct status
    user_name = request.args.get('player')

    if user_name:
        uuid = minecraftApi.get_uuid_from_username(user_name)
        return render_template("spieler-info.html", uuid=uuid, user_name=user_name, status=status)

    all_users = []
    combined_users_data = []
    all_uuids = databasApi.get_all_uuids_from_db()
    for uuid in all_uuids:
        user_name = minecraftApi.get_username_from_uuid(uuid)
        all_users.append(user_name)
        if user_name is None:
            print("No username to " + uuid)

    for i in range(len(all_users)):
        combined_users_data.append([all_users[i], all_uuids[i]])
    return render_template("spieler.html", results=combined_users_data, status=status)


@app.route('/report')
def report_player_route():
    return render_template("report.html")


def check_shutdown():
    print("Start check loop")
    while True:
        print("Looping thru loop")
        if dataBaseOperations.checkForKey("meta", "doAction", "shutdown"):
            mixedApi.doShutdownRoutine()
            break
        time.sleep(5)


if __name__ == '__main__':
    thread = threading.Thread(target=check_shutdown)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True, use_reloader=False)

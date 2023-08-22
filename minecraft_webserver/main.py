import threading
import time
import Logger
from flask import Flask, render_template, request

import dataBaseOperations
import utils

# Logger Setup
logger = Logger.logger()

# Class Setups
minecraftApi = utils.MinecraftApi(logger=logger)
databaseApi = utils.DatabaseApi(logger=logger)
backupApi = utils.BackupApi(logger=logger)
mixedApi = utils.MixedUtilsApi(logger=logger)

# Flask Setup
app = Flask(__name__)
logger.info('Application started')


# Flask Routes
@app.route('/')
def index_route():
    """
    Display the index page.

    :return: Rendered template for the index page (index.html)
    """
    return render_template("index.html")


@app.route('/spieler')
def player_overview_route():  # Untested optimized version
    """
    Display the player overview or specific player information.

    If a player is specified using the "?player=<username>" query parameter,
    the information for that specific player is displayed. Otherwise, the
    general player overview is shown.

    :return: Rendered template for player list or specific player info
             (spieler.html|spieler-info.html)
    """
    user_name = request.args.get('player')

    if user_name:
        uuid = minecraftApi.get_uuid_from_username(user_name)
        status = databaseApi.get_user_status(uuid)
        return render_template("spieler-info.html", uuid=uuid, user_name=user_name, status=status)

    all_users = []
    all_status = []
    combined_users_data = []
    all_uuids = databaseApi.get_all_uuids_from_db()

    for uuid in all_uuids:
        user_name = minecraftApi.get_username_from_uuid(uuid)
        if user_name is None:
            print(f"No username found for UUID: {uuid}")
            continue  # Skip processing if no username found

        all_users.append(user_name)
        status = databaseApi.get_user_status(uuid)
        print(f"Status from user: {user_name} with UUID: {uuid} is: {status}")
        all_status.append(status)
        combined_users_data.append([user_name, uuid])

    print(all_users)
    print(all_uuids)

    return render_template("spieler.html", results=combined_users_data, status=all_status)


@app.route('/report')
def report_player_route():
    """
    Render the report page for reporting players.

    This route function handles requests to the '/report' URL. It renders the 'report.html'
    template, allowing users to report players for various reasons.

    :return: The rendered report page (report.html)
    """
    return render_template("report.html")


# Other main functions
def check_db_events():
    """
    Monitor the thread for various database events:

    1. Check if a shutdown routine needs to be executed.
    2. Monitor the status of players.

    This function continuously checks for database events. If a shutdown action
    is detected, it triggers the shutdown routine and exits the loop. Player
    statuses are also monitored during each iteration.

    :return: None
    """
    print("Starting the check loop")
    while True:
        print("Looping through the loop")

        # Check for shutdown action in the database
        if dataBaseOperations.checkForKey("meta", "doAction", "shutdown"):
            mixedApi.doShutdownRoutine()
            break

        # Check player statuses in the database
        databaseApi.check_for_status()

        time.sleep(5)


if __name__ == '__main__':
    thread = threading.Thread(target=check_db_events)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True, use_reloader=False)

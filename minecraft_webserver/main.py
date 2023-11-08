import datetime
import math
import secrets
import threading
import time
import Logger
from flask import Flask, render_template, request, Response, redirect, session, flash

import dataBaseOperations
import updateDBStats
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
app.config.from_pyfile("config.py")
app.config.from_pyfile("instance/config.py")

proceedStatusUpdate = False


# Flask Routes
@app.route('/')
def index_route():
    """
    Display the index page.

    :return: Rendered template for the index page (index.html)
    """
    return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    db_handler = dataBaseOperations.DatabaseHandler("playerData")

    if request.method == 'POST':
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            form_type = request.form['type']
            if form_type == 'login1':
                username = request.form['username']
                uuid = minecraftApi.get_uuid_from_username(username)
                if uuid is None:
                    print('none')
                    flash("Invalid Minecraft username")
                    db_handler.disconnect()
                    return redirect("/login")
                status = db_handler.get_player_status(uuid)
                print("Player status: " + status)
                if status == "offline":
                    flash('You are not logged into minecraft!')
                    db_handler.disconnect()
                    return redirect("/login")
                secret_pin = secrets.SystemRandom().randrange(100000, 999999)
                print("[DEBUG]: Secret pin: " + str(secret_pin))
                db_handler.create_login_entry(uuid, secret_pin)
                db_handler.disconnect()
                db_handler = dataBaseOperations.DatabaseHandler("interface")
                db_handler.create_login_entry(uuid, secret_pin)
                db_handler.disconnect()
                session["try_login"] = uuid
                return render_template("login2.html")
            elif form_type == "login2":
                uuid = session.get("try_login")
                if uuid is None:
                    session.clear()
                    return redirect("/login")
                if not db_handler.check_for_login_entry(uuid):
                    session.clear()
                    db_handler.disconnect()
                    print("TIMED OUT")
                    flash("timed out")
                    return render_template("login.html")
                try:
                    secret_pin_from_form = int(request.form["pin"])
                except ValueError:
                    flash("Please enter the correct PIN")
                    db_handler.disconnect()
                    return render_template("login2.html")
                if secret_pin_from_form == int(db_handler.get_login_entry(uuid)):
                    print("SUCCESS")
                    session.clear()
                    session["uuid"] = uuid
                    session.permanent = True
                    db_handler.delete_login_entry(uuid)
                    db_handler.disconnect()
                    return redirect("/login")
                else:
                    print(secret_pin_from_form, db_handler.get_login_entry(uuid))
                    flash("Please enter the correct PIN")
                    db_handler.disconnect()
                    return render_template("login2.html")
            else:  # Not a valid request
                db_handler.disconnect()
                return render_template("login.html")
        else:  # Logout command
            input_string = request.form['text_input']
            print(input_string)
            session.clear()
            db_handler.disconnect()
            return render_template("login.html")

    session_var = session.get('uuid')
    print("username: ", session_var)
    if isinstance(session_var, str):
        return render_template("dosth.html", uuid=session_var)
    session_var = session.get('try_login')
    if isinstance(session_var, str):
        return render_template("login2.html")
    return render_template('login.html')


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
        uuid = minecraftApi.get_cached_uuid_from_username(user_name)
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        status = db_handler.get_player_status(uuid)
        # stats = {"minecraft:custom": db_handler.return_complete_column(uuid + "~minecraft:custom", "value"),
        #          "minecraft:broken": db_handler.return_complete_column(uuid + "~minecraft:broken", "value"),
        #          "minecraft:crafted": db_handler.return_complete_column(uuid + "~minecraft:crafted", "value"),
        #          "minecraft:dropped": db_handler.return_complete_column(uuid + "~minecraft:dropped", "value"),
        #          "minecraft:killed_by": db_handler.return_complete_column(uuid + "~minecraft:killed_by", "value"),
        #          "minecraft:killed": db_handler.return_complete_column(uuid + "~minecraft:killed", "value"),
        #          "minecraft:picked_up": db_handler.return_complete_column(uuid + "~minecraft:picked_up", "value"),
        #          "minecraft:used": db_handler.return_complete_column(uuid + "~minecraft:used", "value"),
        #          "minecraft:mined": db_handler.return_complete_column(uuid + "~minecraft:mined", "value")}
        stats_tools, stats_armor, stats_killed, stats_custom, stats_blocks = minecraftApi.get_all_stats(uuid,
                                                                                                        db_handler)
        print("_-----------_")
        print(stats_tools)
        print("_-----------_")

        db_handler.disconnect()
        return render_template("spieler-info.html", uuid=uuid, user_name=user_name, status=status,
                               stats_tools=stats_tools, stats_armor=stats_armor, stats_killed=stats_killed,
                               stats_custom=stats_custom, stats_blocks=stats_blocks)
    all_users = []
    all_status = []
    combined_users_data = []
    all_uuids = databaseApi.get_all_uuids_from_db()

    for uuid in all_uuids:
        user_name = minecraftApi.get_cached_username_from_uuid(uuid)
        if user_name is None:
            print(f"No username found for UUID: {uuid}")
            continue  # Skip processing if no username found

        all_users.append(user_name)
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        status = db_handler.get_player_status(uuid)
        db_handler.disconnect()
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


@app.route('/api/status')
def stream_status():
    def generate():
        while True:
            all_uuids = databaseApi.get_all_uuids_from_db()
            data = []
            for uuid in all_uuids:
                data.append(db_handler.get_player_status(uuid))
            yield f"data: {data}\n\n"
            time.sleep(2)

    db_handler = dataBaseOperations.DatabaseHandler("playerData")
    while not proceedStatusUpdate:
        ...
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/player_info/<path:path>')
def stream_player_info(path):
    player_name = path

    def generate():
        while True:
            # get uuid, get status, get death, get first seen, get last seen, get death time
            uuid = minecraftApi.get_cached_uuid_from_username(player_name)
            status = db_handler.get_player_status(uuid)
            death_count = db_handler.return_specific_key(f"{uuid}~minecraft:custom", "value", "key", "minecraft:deaths")
            first_seen = db_handler.return_specific_key("cache", "first_seen", "UUID", uuid)
            last_seen = db_handler.return_specific_key("cache", "last_seen", "UUID", uuid)
            death_time = db_handler.return_specific_key(f"{uuid}~minecraft:custom", "value", "key",
                                                        "minecraft:time_since_death")
            play_time = db_handler.return_specific_key(f"{uuid}~minecraft:custom", "value", "key",
                                                       "minecraft:play_time")
            death_time = mixedApi.format_time(death_time / 20)
            play_time = mixedApi.format_time(play_time / 20)
            data = [uuid, status, death_count, first_seen, last_seen, death_time, play_time]
            yield f"data: {data}\n\n"
            time.sleep(10)

    db_handler = dataBaseOperations.DatabaseHandler("playerData")

    return Response(generate(), mimetype='text/event-stream')


# Other main functions
def check_db_events():
    global proceedStatusUpdate
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
    counter_2_sec = 9999
    counter_300_sec = 9999
    db_handler = dataBaseOperations.DatabaseHandler("interface")
    statisticUpdater = updateDBStats.StatisticsUpdater()
    while True:
        if counter_300_sec >= 300:
            counter_300_sec = 0
            # Update player stats
            filenames = minecraftApi.list_all_json_file_names()
            for filename in filenames:
                print(filename)
                statisticUpdater.update_game_specific_tables_from_file(filename)
                statisticUpdater.update_player_cache(filename.split('.')[0].replace("-", ""))

        if counter_2_sec >= 2:
            # Check player statuses in the database
            databaseApi.check_for_status()
            proceedStatusUpdate = True
            counter_2_sec = 0
            # Check for shutdown action in the database
            if db_handler.check_for_key("meta", "doAction", "shutdown"):
                mixedApi.do_shutdown_routine()
                break
            proceedStatusUpdate = False

        time.sleep(1)
        counter_2_sec += 1
        counter_300_sec += 1


if __name__ == '__main__':
    minecraftApi.update_blocks()
    thread = threading.Thread(target=check_db_events)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True, use_reloader=False)

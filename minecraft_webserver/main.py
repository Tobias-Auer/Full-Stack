import ast
import datetime
import math
import secrets
import threading
import time
from urllib.parse import urlparse

import Logger
from flask import Flask, render_template, request, Response, redirect, session, flash, jsonify, abort, url_for
import flaskLogin
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
FL = flaskLogin.FlaskLogin(logger=logger)

# Flask Setup
app = Flask(__name__)
logger.info('Application started')
app.config.from_pyfile("config.py")
app.config.from_pyfile("instance/config.py")


@app.context_processor
def inject_loginVar():
    uuid = session.get('uuid')
    loginVar = "<a href=\"/login\" id=loginLink>Login</a>"
    if isinstance(uuid, str):
        name = minecraftApi.get_username_from_uuid(uuid)
        loginVar = f"<div>Willkommen {name}<br> <a href=\"/login\" id=logoutLink>Logout</a></div>"

    return dict(loginVar=loginVar)


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
            form_type = request.form['type']  # form type specifies which login form was submitted
            if form_type == 'login1':
                username = request.form['username']
                uuid = minecraftApi.get_uuid_from_username(username)
                if uuid is None:
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
                db_handler.create_login_entry(uuid, secret_pin)
                db_handler.disconnect()
                db_handler = dataBaseOperations.DatabaseHandler("interface")
                db_handler.create_login_entry(uuid, secret_pin)
                db_handler.disconnect()
                session["try_login"] = uuid  # set session cookie for the next step in the login process
                return render_template("login2.html")
            elif form_type == "login2":
                uuid = session.get("try_login")
                if uuid is None:  # error correction if sth is wrong
                    session.clear()
                    return redirect("/login")
                if not db_handler.check_for_login_entry(uuid):  # happens after the 5-minute timeout
                    session.clear()
                    db_handler.disconnect()
                    flash("timed out")
                    return render_template("login.html")
                try:
                    secret_pin_from_form = int(request.form["pin"])
                except ValueError:
                    flash("Please enter the correct PIN")
                    db_handler.disconnect()
                    return render_template("login2.html")
                if secret_pin_from_form == int(db_handler.get_login_entry(uuid)):
                    session.clear()
                    session["uuid"] = uuid
                    session.permanent = True
                    db_handler.delete_login_entry(uuid)
                    db_handler.disconnect()
                    next = request.args.get('next')
                    if not next:
                        return redirect("/")
                    return redirect(next)
                else:
                    print(secret_pin_from_form, db_handler.get_login_entry(uuid))
                    flash("Please enter the correct PIN")
                    db_handler.disconnect()
                    return render_template("login2.html")
            else:  # Not a valid request
                db_handler.disconnect()
                return render_template("login.html")
        else:  # Probably Logout command
            db_handler.disconnect()  # close connection bc it's not further needed but still open
            input_string = request.form['text_input']
            if input_string != "logout":
                abort(400)
            session.clear()

            return render_template("login.html")

    uuid = session.get('uuid')
    print("username: ", uuid)
    if isinstance(uuid, str):
        return render_template("logout_confirmation.html", uuid=uuid)
    uuid = session.get('try_login')
    if isinstance(uuid, str):
        return render_template("login2.html")
    if not request.args.get('next'):
        refer = request.referrer
        path = "/" if not refer else urlparse(refer).path

        return redirect(f'/login?next={path}')
    return render_template("login.html")


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/spieler')
def player_overview_route():
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
        stats_tools, stats_armor, stats_killed, stats_custom, stats_blocks = minecraftApi.get_all_stats(uuid,
                                                                                                        db_handler)

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


@app.route('/add_pref')
@FL.require_auth()
def add_pref_path():
    db_handler = dataBaseOperations.DatabaseHandler("prefix")
    pref = db_handler.get_pref(session.get("uuid"))
    db_handler.disconnect()
    prefix = ""
    color = ""
    if pref[0]:
        prefix = pref[1].split("[")[1].replace("]", "")
        color = pref[1].split("[")[0]
    return render_template("create-prefix.html", prefix=prefix, color=color)


@app.route('/manage_pref')
def manage_pref_path():
    return redirect("/add_pref")  # TODO: Delete route and link in header


@app.route('/join_pref')
def join_pref_path():
    return "lol"


@app.route('/pref_api', methods=['POST'])
def pref_api():
    data = request.json
    prefixName = data['playerName']
    color = data['color']
    password = data['password']
    uuid = session.get("uuid")

    db_handler = dataBaseOperations.DatabaseHandler("prefix")
    if len(prefixName) > 10:
        response_data = {'result': 'denied', "reason": "length"}
        return jsonify(response_data)
    if color not in ["§e", "§b", "§3", "§1", "§9", "§d", "§5", "§f", "§7", "§8", "§0"] or prefixName == "":
        response_data = {'result': 'denied', "reason": "invalid color or name"}
        return jsonify(response_data)
    with open("blacklist.txt", 'r') as file:
        blacklist = ast.literal_eval(file.readline())
    if prefixName.lower().replace(" ", "") in blacklist:
        response_data = {'result': 'denied', "reason": "blacklist"}
        return jsonify(response_data)

    result = db_handler.write_prefix(uuid, prefixName, color, password)
    db_handler.disconnect()

    response_data = {'result': result}
    return jsonify(response_data)


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

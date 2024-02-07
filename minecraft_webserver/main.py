import ast
import os
import secrets
import sys
import threading
import time
from urllib.parse import urlparse

from flask import Flask, render_template, request, Response, redirect, session, flash, jsonify, abort

import Logger
import dataBaseOperations
import flaskLogin
import updateDBStats
import utils

if sys.platform.lower() == "win32":  # cmd color support patch
    os.system('color')
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
    permission_level = 99
    if isinstance(uuid, str):
        name = minecraftApi.get_username_from_uuid(uuid)
        loginVar = (f"<div>Willkommen {name}<br> <a id=logoutLink onclick=\"logout()\" style=\"cursor: "
                    "pointer;\">Logout</a></div>")
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        permission_level = db_handler.get_access_level(uuid)
        db_handler.disconnect()

    return dict(loginVar=loginVar, perm=permission_level)


proceedStatusUpdate = False  # multithreading lock


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
        # Probably Logout command
        db_handler.disconnect()  # close connection bc it's not further needed but still open
        input_string = request.form['text_input']
        if input_string != "logout":
            abort(400)
        session.clear()
        return render_template("index.html")

    uuid = session.get('uuid')
    print("username: ", uuid)
    if isinstance(uuid, str):
        return render_template("logout_confirmation.html", uuid=uuid)
    uuid = session.get('try_login')
    if isinstance(uuid, str):
        return render_template("new-login.html", uuid=minecraftApi.get_cached_username_from_uuid(uuid))
    if not request.args.get('next'):
        refer = request.referrer
        path = "/" if not refer else urlparse(refer).path
        return redirect(f'/login?next={path}')
    return render_template("new-login.html", uuid="")


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/unban')
def unban_route():
    return "Machs einfach hier <a href='https://www.discord.gg/vJYNnsQwf8' target='_blank'>Discord</a>"


@app.route('/report')
def report_route():
    return "Machs einfach hier <a href='https://www.discord.gg/vJYNnsQwf8' target='_blank'>Discord</a>"


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
        enddate, startdate = "", ""
        banned = db_handler.get_banned_status(uuid)
        if banned == "True":
            startdate, enddate = db_handler.get_banned_dates(uuid)

        db_handler.disconnect()
        return render_template("spieler-info.html", uuid=uuid, user_name=user_name, status=status,
                               stats_tools=stats_tools, stats_armor=stats_armor, stats_killed=stats_killed,
                               stats_custom=stats_custom, stats_blocks=stats_blocks, banned=banned, enddate=enddate,
                               startdate=startdate)

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


@app.route("/users", methods=["GET", "POST"])
@FL.require_auth(1)
def users_route():
    db_handler = dataBaseOperations.DatabaseHandler("playerData")
    print(request.method)
    if request.method == "POST" and request.headers.get('Content-Type') == 'application/json':
        print("received POST request")
        data = request.json
        print(data)
        mode = data.get('mode')
        if mode == "lvl":
            uuid, new_access_lvl = data.get("uuid"), data.get("new_access_lvl")
            db_handler.change_access_level(uuid, new_access_lvl)
        elif mode == "ban":
            uuid, state = data.get("uuid"), data.get("state")
            print(f"Received {state} to {uuid}")
            if state == "ban":
                db_handler.ban_player(uuid)
            elif state == "unban":
                db_handler.unban_player(uuid)
        db_handler.disconnect()
        return jsonify("{success:success}")
    user_list = db_handler.return_table("cache")
    print(user_list)
    db_handler.disconnect()
    return render_template("users.html", data=user_list)


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


@FL.require_auth()
@app.route('/join_pref', methods=["GET", "POST"])
def join_pref_path():
    db_handler = dataBaseOperations.DatabaseHandler("prefix")
    if request.method == 'POST' and request.headers.get('Content-Type', '') == 'application/json':
        apply_mode = request.get_json()["apply_mode"]
        requested_prefix = request.get_json()["prefix"]
        password = request.get_json()["pwd"]
        changed_prefix_success = False
        changed_prefix_error = ""
        print(request.get_json())

        prefix_check_switch, require_pwd = db_handler.check_for_prefix(requested_prefix, password,
                                                                       apply_mode)  # check for existence and pwd

        if apply_mode:
            if not prefix_check_switch:
                changed_prefix_success = False
                changed_prefix_error = "Falsches Passwort angegeben!"
            else:
                status = db_handler.apply_prefix(session.get('uuid'), requested_prefix)
                changed_prefix_success = status[0]
                if not changed_prefix_success:  # error occurred
                    changed_prefix_error = status[1]

        return jsonify(apply_mode=apply_mode, requested_prefix=requested_prefix, allowed=prefix_check_switch,
                       require_pwd=require_pwd,
                       success=changed_prefix_success, reason=changed_prefix_error)

    all_available_prefixes = db_handler.get_all_pref()

    db_handler.disconnect()
    return render_template("prefixes.html", results=all_available_prefixes)


@app.route('/pref_api', methods=['POST'])
def pref_api():
    data = request.json
    prefixName = data['playerName']
    color = data['color']
    password = data['password']
    if password == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":  # --> ''
        password = None
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
    if prefixName.lower().replace(" ", "") in blacklist or prefixName.lower().replace(" ", "").find("owner") != -1:
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
    while not proceedStatusUpdate:  # threading lock(my best try at least, not sure if it is the correct way to do this)
        ...
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/player_count')
def stream_player_count():
    def generate():
        while True:
            online_count = db_handler.get_player_status(None, True)
            yield f"data: {online_count}\n\n"
            time.sleep(10)

    db_handler = dataBaseOperations.DatabaseHandler("playerData")
    while not proceedStatusUpdate:  # threading lock (my best try at least, not sure whether this is the correct way of doing this)
        ...
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/login', methods=['POST'])
def login_api():
    db_handler = dataBaseOperations.DatabaseHandler("playerData")
    if not request.headers.get('Content-Type', '') == 'application/json':
        return {'response': "Invalid content"}
    username = request.get_json()["username"]
    pin = request.get_json()["pin"]

    print(f"Username: '{username}', Password: '{pin}'")

    if not pin:
        if pin == "":
            return {'response': "Invalid pin", "status": "error",
                    "info": "Please enter a valid pin!"}
        uuid = minecraftApi.get_uuid_from_username(username)
        if uuid is None:
            db_handler.disconnect()
            return {'response': "Invalid username", "status": "error",
                    "info": "Given username not found in the database"}
        status = db_handler.get_player_status(uuid)
        print("Player status: " + status)
        if status == "offline":
            db_handler.disconnect()
            return {'response': "You are offline", "status": "error",
                    "info": "Please log into the server and try again. You must be online to progress"}
        secret_pin = secrets.SystemRandom().randrange(100000, 999999)
        db_handler.create_login_entry(uuid, secret_pin)
        db_handler.disconnect()
        db_handler = dataBaseOperations.DatabaseHandler("interface")
        db_handler.create_login_entry(uuid, secret_pin)
        db_handler.disconnect()
        session["try_login"] = uuid  # set session cookie for the next step in the login process
        print("successfully done sth")
        return {"response": "success", "status": "success", "info": ""}
    else:
        uuid = session.get("try_login")
        if uuid is None:  # error correction if sth is wrong
            session.clear()
            return {"response": "Cookie is wrong", "status": "reset",
                    "info": "Something with your cookies went wrong! Did you eat any of them?? Please try again!"}
        if not db_handler.check_for_login_entry(uuid):  # happens after the 5-minute timeout
            session.clear()
            db_handler.disconnect()
            return {"response": "Timed out", "status": "reset",
                    "info": "Your pin has timed out. You have 5 only minutes to enter your pin until it gets devalidated! Please try again!"}
        try:
            secret_pin_from_form = int(pin)
        except ValueError:
            db_handler.disconnect()
            return {"response": "Pin is incorrect", "status": "error",
                    "info": "Your pin is incorrect! Please try again!"}
        if secret_pin_from_form == int(db_handler.get_login_entry(uuid)):
            session.clear()
            session["uuid"] = uuid
            session.permanent = True
            db_handler.delete_login_entry(uuid)
            db_handler.disconnect()
            return {"response": "Pin is correct", "status": "success", "info": ""}
        else:
            print(secret_pin_from_form, db_handler.get_login_entry(uuid))
            db_handler.disconnect()
            return {"response": "Pin is incorrect", "status": "error",
                    "info": "Your pin is incorrect! Please try again!"}


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
    global proceedStatusUpdate, webserver_start_delay
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
    # yeah, i know sth. like webhooks would be better but i don't know how to send data from a docker container to an
    # api bc of the docker restrictions and im too stupid and lazy to figure it out thats why im doing it that way (if
    # anyone ever read this and know how i could do that with webhooks or sth else so that my code dont have to
    # check the db every few seconds even if there is no data in it then contact me or make a pull request. pls :) )
    counter_2_sec = 9999
    counter10_sec = 9999
    counter_300_sec = 9999
    db_handler = dataBaseOperations.DatabaseHandler("interface")
    db_handler_ban = dataBaseOperations.DatabaseHandler("ban_interface")
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

        if counter10_sec >= 10:
            if db_handler_ban.check_for_key("status", "mc_server_changed_sth", "True"):
                db_handler_ban.delete_key("status", "mc_server_changed_sth", "True")
                toggle_ban_state = db_handler_ban.get_ban_entries()

                db_handler_pd = dataBaseOperations.DatabaseHandler("playerData")
                db_handler_pd.toggle_ban_state(toggle_ban_state, "True")
                db_handler_pd.disconnect()
            counter10_sec = 0

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
        counter10_sec += 1
        counter_300_sec += 1


if __name__ == '__main__':
    minecraftApi.update_blocks()
    databaseApi.clean_db()
    thread = threading.Thread(target=check_db_events)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True, use_reloader=False)

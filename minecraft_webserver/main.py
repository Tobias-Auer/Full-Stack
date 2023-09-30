import datetime
import threading
import time
import Logger
from flask import Flask, render_template, request, Response

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

proceedStatusUpdate = False


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
        uuid = minecraftApi.get_cached_uuid_from_username(user_name)
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        status = db_handler.get_player_status(uuid)
        stats = {"minecraft:custom": db_handler.return_complete_column(uuid + "~minecraft:custom", "value"),
                 "minecraft:broken": db_handler.return_complete_column(uuid + "~minecraft:broken", "value"),
                 "minecraft:crafted": db_handler.return_complete_column(uuid + "~minecraft:crafted", "value"),
                 "minecraft:dropped": db_handler.return_complete_column(uuid + "~minecraft:dropped", "value"),
                 "minecraft:killed_by": db_handler.return_complete_column(uuid + "~minecraft:killed_by", "value"),
                 "minecraft:killed": db_handler.return_complete_column(uuid + "~minecraft:killed", "value"),
                 "minecraft:picked_up": db_handler.return_complete_column(uuid + "~minecraft:picked_up", "value"),
                 "minecraft:used": db_handler.return_complete_column(uuid + "~minecraft:used", "value"),
                 "minecraft:mined": db_handler.return_complete_column(uuid + "~minecraft:mined", "value")}

        tools_substrings = ["axe", "shovel", "hoe", "sword", "pickaxe", "shield"]
        tools_broken_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:broken", "key",
                                                                           tools_substrings)
        tools_broken_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:broken", "key", "value",
                                                                           tools_substrings)
        tools_broken = dict(zip(tools_broken_names, tools_broken_stats))

        tools_crafted_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:crafted", "key",
                                                                            tools_substrings)
        tools_crafted_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:crafted", "key", "value",
                                                                            tools_substrings)
        tools_crafted = dict(zip(tools_crafted_names, tools_crafted_stats))

        tools_dropped_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:dropped", "key",
                                                                            tools_substrings)
        tools_dropped_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:crafted", "key", "value",
                                                                            tools_substrings)
        tools_dropped = dict(zip(tools_dropped_names, tools_dropped_stats))

        tools_picked_up_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:picked_up", "key",
                                                                              tools_substrings)
        tools_picked_up_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:picked_up", "key",
                                                                              "value", tools_substrings)
        tools_picked_up = dict(zip(tools_picked_up_names, tools_picked_up_stats))

        tools_used_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:used", "key",
                                                                         tools_substrings)
        tools_used_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:used", "key", "value",
                                                                         tools_substrings)
        tools_used = dict(zip(tools_used_names, tools_used_stats))

        tools_names = list(
            set(tools_broken_names + tools_crafted_names + tools_dropped_names + tools_picked_up_names + tools_used_names))

        stats_tools = {}
        # check every single dict if current tool is present(key) if so, get value otherwise value is 0
        for tool_name in tools_names:
            stat_list = [tools_broken.get(tool_name, 0), tools_crafted.get(tool_name, 0),
                         tools_dropped.get(tool_name, 0), tools_picked_up.get(tool_name, 0),
                         tools_used.get(tool_name, 0)]
            stats_tools.update({tool_name: stat_list})

        ################################
        armor_substrings = ["boots", "leggings", "chestplate", "helmet"]
        armor_broken_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:broken", "key",
                                                                           armor_substrings)
        armor_broken_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:broken", "key", "value",
                                                                           armor_substrings)
        armor_broken = dict(zip(armor_broken_names, armor_broken_stats))

        armor_crafted_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:crafted", "key",
                                                                            armor_substrings)
        armor_crafted_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:crafted", "key", "value",
                                                                            armor_substrings)
        armor_crafted = dict(zip(armor_crafted_names, armor_crafted_stats))

        armor_dropped_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:dropped", "key",
                                                                            armor_substrings)
        armor_dropped_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:crafted", "key", "value",
                                                                            armor_substrings)
        armor_dropped = dict(zip(armor_dropped_names, armor_dropped_stats))

        armor_picked_up_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:picked_up", "key",
                                                                              armor_substrings)
        armor_picked_up_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:picked_up", "key",
                                                                              "value", armor_substrings)
        armor_picked_up = dict(zip(armor_picked_up_names, armor_picked_up_stats))

        armor_used_names = db_handler.return_complete_column_filter_like(uuid + "~minecraft:used", "key",
                                                                         armor_substrings)
        armor_used_stats = db_handler.return_specific_values_with_filter(uuid + "~minecraft:used", "key", "value",
                                                                         armor_substrings)
        armor_used = dict(zip(armor_used_names, armor_used_stats))

        armor_names = list(
            set(armor_broken_names + armor_crafted_names + armor_dropped_names + armor_picked_up_names + armor_used_names))

        stats_armor = {}
        # check every single dict if current tool is present(key) if so, get value otherwise value is 0
        for tool_name in armor_names:
            stat_list = [armor_broken.get(tool_name, 0), armor_crafted.get(tool_name, 0),
                         armor_dropped.get(tool_name, 0), armor_picked_up.get(tool_name, 0),
                         armor_used.get(tool_name, 0)]
            stats_armor.update({tool_name: stat_list})
        ################

        killed_names = db_handler.return_complete_column(uuid + "~minecraft:killed", "key")
        killed_stats = db_handler.return_complete_column(uuid + "~minecraft:killed", "value")
        killed = dict(zip(killed_names, killed_stats))

        killed_by_names = db_handler.return_complete_column(uuid + "~minecraft:killed_by", "key")
        killed_by_stats = db_handler.return_complete_column(uuid + "~minecraft:killed_by", "value")
        killed_by = dict(zip(killed_by_names, killed_by_stats))

        killed_names_all = list(set(killed_names + killed_by_names))
        stats_killed = {}
        # check every single dict if current tool is present(key) if so, get value otherwise value is 0
        for tool_name in killed_names_all:
            stat_list = [killed.get(tool_name, 0), killed_by.get(tool_name, 0)]
            stats_killed.update({tool_name: stat_list})
        ################

        db_handler.disconnect()
        return render_template("spieler-info.html", uuid=uuid, user_name=user_name, status=status, stats=stats,
                               stats_tools=stats_tools, stats_armor=stats_armor, stats_killed=stats_killed)
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
        print("Looping through the loop")
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
    thread = threading.Thread(target=check_db_events)
    thread.start()
    app.run(host="0.0.0.0", port=80, threaded=True, debug=True, use_reloader=False)

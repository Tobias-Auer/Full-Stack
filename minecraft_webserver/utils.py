import os
import re
from datetime import datetime
from zipfile import ZipFile

import requests

import dataBaseOperations


class BackupApi:
    """
    Class for handling backups.
    """

    def __init__(self, logger=None):
        """
        Initialize the BackupApi instance.

        :param logger: Logger object for logging
        """
        self.logger = logger

    def make_backup(self):
        """
        Create a backup from the paths defined in "backupPaths".

        :return: True if the backup was successful, otherwise False.
        """
        self.logger.info("Creating backup")
        base_path = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1"
        backup_paths = ["logs", "world", "world_nether", "world_the_end", "plugins"]  # Remove the leading backslashes
        target_path = fr"E:\backups_mc\{datetime.now().strftime('%Y-%m-%d %H.%M.%S')}"
        self.logger.debug("base_path: %s", base_path)
        self.logger.debug("backup_paths: %s", backup_paths)
        self.logger.debug("target_path: %s", target_path)

        try:
            with ZipFile(f'{target_path}.zip', 'w') as zip_object:
                for path in backup_paths:
                    self.logger.info(f"Start to backup: {path}")
                    path = os.path.join(base_path, path)
                    for folder_name, sub_folders, file_names in os.walk(path):
                        for filename in file_names:
                            if filename.endswith(".jar"):
                                continue
                            file_path = os.path.join(folder_name, filename)
                            zip_object.write(file_path, os.path.relpath(file_path, base_path))
                    self.logger.info(f"Done with {path}")
        except Exception as e:
            self.logger.error("[ERROR] Error during backup:")
            self.logger.error(e)
            return False

        if os.path.exists(f'{target_path}.zip'):
            self.logger.info("Backup successfully created")
            return True
        else:
            self.logger.error("[ERROR] Unknown error, zip is not created properly")
            return False

    def do_backup_routine(self):
        """
        Perform the backup routine.

        :return: True if the backup was successful, otherwise False.
        """
        self.logger.info("Backup recognized")
        backup_status = self.make_backup()
        if backup_status:
            self.logger.info("Backup created successfully")
        else:
            self.logger.error("Failed to create backup")
        return backup_status


class MixedUtilsApi:
    """
    Class containing various utility methods.
    """

    def __init__(self, logger=None):
        """
        Initialize the MixedUtilsApi instance.

        :param logger: Logger object for logging.
        """
        self.logger = logger

    def do_shutdown_routine(self):
        """
        Perform the shutdown routine:
        - Delete the shutdown key from the database
        - If a backup is needed, call "backupApi.do_backup_routine()"
        - Shutdown the computer with a 60-second timeout.

        :return: None
        """
        self.logger.info("Shutdown routine recognized")
        db_handler = dataBaseOperations.DatabaseHandler("interface")
        shutdown_key_delete_status = db_handler.delete_key("meta", "doAction", "shutdown")
        if shutdown_key_delete_status:
            self.logger.debug("Shutdown key deleted from database")
        else:
            self.logger.error(shutdown_key_delete_status)

        if db_handler.check_for_key("meta", "doAction", "backup"):
            backup_api = BackupApi(self.logger)
            backup_api.do_backup_routine()
            backup_key_delete_status = db_handler.delete_key("meta", "doAction", "backup")
            if backup_key_delete_status:
                self.logger.debug("Backup key deleted from database")
            else:
                self.logger.error(backup_key_delete_status)
        else:
            self.logger.info("Backup skipped")
        db_handler.disconnect()
        os.system("shutdown -s")
        self.logger.info("Shutdown initiated")
        exit()

    def format_time(self, seconds):
        """
        Formats a given number of seconds into a human-readable time string.

        Args:
            seconds (int): The number of seconds to be formatted.

        Returns:
            str: A formatted time string in the format "X Tage, Y Stunden, Z Minuten, W Sekunden",
                 where the parts are included only if they are non-zero.
        """
        days = int(seconds // 86400)
        seconds %= 86400

        hours = int(seconds // 3600)
        seconds %= 3600

        minutes = int(seconds // 60)
        seconds = int(seconds % 60)

        time_parts = []
        if days > 0:
            time_parts.append(f"{days} Tag{'e' if days > 1 else ''}")
        if hours > 0:
            time_parts.append(f"{hours} Stunde{'n' if hours > 1 else ''}")
        if minutes > 0:
            time_parts.append(f"{minutes} Minute{'n' if minutes > 1 else ''}")
        if seconds > 0:
            time_parts.append(f"{seconds} Sekunde{'n' if seconds > 1 else ''}")

        return ', '.join(time_parts)


class DatabaseApi:
    """
    Class containing various methods to interact with the database.
    """

    def __init__(self, logger=None):
        """
        Initialize the DatabaseApi instance.

        :param logger: Logger object for logging.
        """
        self.logger = logger

    def get_all_uuids_from_db(self):
        """
        Get all tables from the database, split them at "~" to extract the uuid, and add them to the "unique_uuids"
        list.

        :return: List containing all known uuids.
        """
        unique_uuids = []
        regex = r"^[A-F\d]{8}[A-F\d]{4}4[A-F\d]{3}[89AB][A-F\d]{3}[A-F\d]{12}$"

        try:
            db_handler = dataBaseOperations.DatabaseHandler("playerData")
            all_tables = db_handler.list_all_tables()
            db_handler.disconnect()
            unique_uuids = []

            for table in all_tables:
                uuid = str(table[0]).split('~')[0]
                if uuid not in unique_uuids:
                    print("Checking regex: '%s'" % uuid)
                    if re.search(regex, uuid, re.IGNORECASE):
                        print("Matched regex")
                        unique_uuids.append(uuid)
                    else:
                        print("Matched no regex")
        except Exception as e:

            self.logger.error(e)
            if self.logger is None:
                print(e)
        finally:
            return unique_uuids

    def check_for_status(self):
        """
        Check for new entries in the "data.db" database and update them in the "player_data.db" database accordingly.

        :return: None
        """
        print("start check for status")
        db_handler = dataBaseOperations.DatabaseHandler("interface")

        status_list = db_handler.return_complete_column("status", "status")
        for status_entry in status_list:
            if status_entry[0] is None or "~" not in status_entry[0]:
                print(f"Skipped status entry: {status_entry}")
                continue
            print("Status entry:" + str(status_entry))
            player_uuid, player_status = status_entry[0].split("~")
            player_uuid.replace("-", "")
            print(f"Updating player status for player: {player_uuid} to {player_status}")
            self.__update_player_status(player_uuid, player_status)
            db_handler.delete_key("status", "status", status_entry[0])
        db_handler.disconnect()

        print("done with check for status")

    @staticmethod
    def __update_player_status(player_uuid, status):
        """
        Update the status of the player identified by player_uuid.

        :param player_uuid: UUID of the player.
        :param status: Status of the player.
        :return: None
        """
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        db_handler.write_player_status(player_uuid, status)
        db_handler.disconnect()


class MinecraftApi:
    """
    Class containing various methods in relation to Minecraft.
    """

    def __init__(self, logger=None):
        """
        Initialize the MinecraftApi instance.

        :param logger: Logger object for logging.
        """
        self.logger = logger
        self.mixedApi = MixedUtilsApi(logger=logger)

    def list_all_json_file_names(self):
        """
        List all the JSON files in the "C:/Users/balus/OneDrive/Desktop/mc-docker-1.20.1/world/stats" folder.
        :return: All filenames in list
        """
        print("start reading files")
        json_files = []
        for filename in os.listdir(r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\world\stats"):
            print(filename)
            if filename.endswith(".json"):
                json_files.append(filename)
        return json_files

    def get_username_from_uuid(self, UUID):
        """
        Get the username from the Mojang API using the given UUID.

        :param UUID: UUID of the player.
        :return: str: The username of the requested player.
        """
        URL = f"https://api.mojang.com/user/profile/{UUID}"
        user_name = None
        try:
            response = requests.get(URL)
            if response.status_code == 200:
                data = response.json()
                user_name = data.get("name")
        except Exception as e:
            self.logger.error("Error in get_username_from_uuid: " + str(e))
            if self.logger is None:
                print(e)
        finally:
            if (user_name is
                    None):
                user_name = "error"
            return user_name

    def get_uuid_from_username(self, username):
        """
        Get the UUID from the Mojang API using the given username.

        :param username: Username of the player.
        :return: str: The UUID of the requested player.
        """
        uuid = None
        URL = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        try:
            response = requests.get(URL)
            if response.status_code == 200:
                data = response.json()
                uuid = data.get("id")
        except Exception as e:
            self.logger.error(e)
            if self.logger is None:
                print(e)
        finally:
            return uuid

    def get_cached_uuid_from_username(self, user_name):
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        uuid = db_handler.return_specific_key("cache", "UUID", "name", user_name)
        db_handler.disconnect()
        return uuid

    def get_cached_username_from_uuid(self, uuid):
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        name = db_handler.return_specific_key("cache", "name", "UUID", uuid)
        db_handler.disconnect()
        return name

    @staticmethod
    def merge_stats_dicts(names, *stat_dicts):
        stats = {}
        for tool_name in names:
            stat_list = [stat.get(tool_name, 0) for stat in stat_dicts]
            stats[tool_name] = stat_list
        return stats

    def get_all_stats(self, uuid, db_handler):
        tools_substrings = ["axe", "shovel", "hoe", "sword", "pickaxe", "shield"]
        armor_substrings = ["boots", "leggings", "chestplate", "helmet"]
        block_substrings = list(db_handler.return_complete_column("blockInformation", "blocks")[0])[0]

        def get_stats_tools():
            tools_broken = db_handler.return_table(f"{uuid}~minecraft:broken")
            tools_broken = dict((key, value) for key, value in tools_broken if any(substring in key for substring in tools_substrings))
            tools_crafted = db_handler.return_table(f"{uuid}~minecraft:crafted")
            tools_crafted = dict((key, value) for key, value in tools_crafted if any(substring in key for substring in tools_substrings))
            tools_dropped = db_handler.return_table(f"{uuid}~minecraft:dropped")
            tools_dropped = dict((key, value) for key, value in tools_dropped if any(substring in key for substring in tools_substrings))
            tools_picked_up = db_handler.return_table(f"{uuid}~minecraft:picked_up")
            tools_picked_up = dict((key, value) for key, value in tools_picked_up if any(substring in key for substring in tools_substrings))
            tools_used = db_handler.return_table(f"{uuid}~minecraft:used")
            tools_used = dict((key, value) for key, value in tools_used if any(substring in key for substring in tools_substrings))

            tools_names = list(set(
                list(tools_broken.keys()) + list(tools_crafted.keys()) + list(tools_dropped.keys()) + list(
                    tools_picked_up.keys()) + list(tools_used.keys())))

            stats_tools = self.merge_stats_dicts(tools_names, tools_broken, tools_crafted, tools_dropped,
                                                 tools_picked_up, tools_used)

            return stats_tools

        def get_stats_armor():
            armor_broken = db_handler.return_table(f"{uuid}~minecraft:broken")
            armor_broken = dict((key, value) for key, value in armor_broken if any(substring in key for substring in armor_substrings))
            armor_crafted = db_handler.return_table(f"{uuid}~minecraft:crafted")
            armor_crafted = dict((key, value) for key, value in armor_crafted if any(substring in key for substring in armor_substrings))
            armor_dropped = db_handler.return_table(f"{uuid}~minecraft:dropped")
            armor_dropped = dict((key, value) for key, value in armor_dropped if any(substring in key for substring in armor_substrings))
            armor_picked_up = db_handler.return_table(f"{uuid}~minecraft:picked_up")
            armor_picked_up = dict((key, value) for key, value in armor_picked_up if any(substring in key for substring in armor_substrings))
            armor_used = db_handler.return_table(f"{uuid}~minecraft:used")
            armor_used = dict((key, value) for key, value in armor_used if any(substring in key for substring in armor_substrings))

            armor_names = list(set(
                list(armor_broken.keys()) + list(armor_crafted.keys()) + list(armor_dropped.keys()) + list(
                    armor_picked_up.keys()) + list(armor_used.keys())))

            stats_armor = self.merge_stats_dicts(armor_names, armor_broken, armor_crafted, armor_dropped,
                                                 armor_picked_up, armor_used)
            return stats_armor

        def get_stats_blocks():
            blocks_mined = db_handler.return_table(f"{uuid}~minecraft:mined")
            blocks_mined = dict([(key, value) for key, value in blocks_mined if key in block_substrings])
            blocks_placed = db_handler.return_table(f"{uuid}~minecraft:used")
            blocks_placed = dict([(key, value) for key, value in blocks_placed if key in block_substrings])
            blocks_picked_up = db_handler.return_table(f"{uuid}~minecraft:picked_up")
            blocks_picked_up = dict([(key, value) for key, value in blocks_picked_up if key in block_substrings])
            blocks_dropped = db_handler.return_table(f"{uuid}~minecraft:dropped")
            blocks_dropped = dict([(key, value) for key, value in blocks_dropped if key in block_substrings])
            blocks_crafted = db_handler.return_table(f"{uuid}~minecraft:crafted")
            blocks_crafted = dict([(key, value) for key, value in blocks_crafted if key in block_substrings])

            blocks_names = list(
                set(list(blocks_mined.keys()) + list(blocks_placed.keys()) + list(blocks_picked_up.keys()) + list(
                    blocks_dropped.keys()) + list(blocks_crafted.keys())))

            stats_blocks = self.merge_stats_dicts(blocks_names, blocks_mined, blocks_placed, blocks_picked_up,
                                                  blocks_dropped, blocks_crafted)

            return stats_blocks

        def get_stats_killed():
            killed_names = db_handler.return_complete_column(uuid + "~minecraft:killed", "key")
            killed_stats = db_handler.return_complete_column(uuid + "~minecraft:killed", "value")
            killed = dict(zip(killed_names, killed_stats))

            killed_by_names = db_handler.return_complete_column(uuid + "~minecraft:killed_by", "key")
            killed_by_stats = db_handler.return_complete_column(uuid + "~minecraft:killed_by", "value")
            killed_by = dict(zip(killed_by_names, killed_by_stats))

            killed_names_all = list(set(killed_names + killed_by_names))

            stats_killed = self.merge_stats_dicts(killed_names_all, killed, killed_by)
            try:
                del stats_killed["Null"]  # remove some Null's from stats if tables are missing
            except KeyError:
                pass
            return stats_killed

        def get_stats_custom():
            custom_names = db_handler.return_complete_column(uuid + "~minecraft:custom", "key")
            custom_stats = db_handler.return_complete_column(uuid + "~minecraft:custom", "value")

            for index, item in enumerate(custom_names):
                if "time" in item[0]:
                    custom_stats[index] = str(self.mixedApi.format_time(int(custom_stats[index][0]) // 20))
            custom = dict(zip(custom_names, custom_stats))
            custom_names_all = custom_names

            stats_custom = self.merge_stats_dicts(custom_names_all, custom)
            return stats_custom

        return get_stats_tools(), get_stats_armor(), get_stats_killed(), get_stats_custom(), get_stats_blocks()

    def update_blocks(self):
        """
        This function updates the valid blocks in the game and insert them into the database Runs every time the
        server is started and checks hash of the file to check if it has changed to save resouurces when the server
        starts.
        File source: https://github.com/PrismarineJS/minecraft-data/blob/master/data/pc/1.20/blocks.json

        Filename: blocks.json
        :return:
        """
        import json
        file_path = 'blocks.json'
        import hashlib

        BUF_SIZE = 65536
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                md5.update(data)
        md5_hash = md5.hexdigest().lower()
        db_handler = dataBaseOperations.DatabaseHandler("playerData")
        db_md5_hash = db_handler.return_complete_column("blockInformation", "hash")[0][0].lower()
        print(md5_hash)
        print(db_md5_hash)
        if md5_hash == db_md5_hash:
            print("same")
            db_handler.disconnect()
            return

        name_list = []

        with open(file_path, 'r') as file:
            data = json.load(file)

        for item in data:
            name_list.append(item["name"])

        print(name_list)
        db_handler.write_specific_value("blockInformation", "hash", db_md5_hash, "blocks", str(name_list))
        db_handler.write_specific_value("blockInformation", "hash", db_md5_hash, "hash", str(md5_hash))
        db_handler.disconnect()


if __name__ == '__main__':
    ...

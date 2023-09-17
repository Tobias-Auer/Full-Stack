import os
import re
from datetime import datetime
from zipfile import ZipFile

import requests

import dataBaseOperations


class BackupApi:  # Untested optimized version
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


if __name__ == '__main__':
    api = MinecraftApi()
    # print(api.get_uuid_from_username("_Tobias4444"))
    # print(api.get_username_from_uuid("4ebe5f6fc23143159d60097c48cc6d30"))
    # dataApi = DatabaseApi()
    # dataApi.get_all_uuids_from_db()
    # dataApi.check_for_status()
    print(api.get_cached_uuid_from_username("_Tobias4444"))

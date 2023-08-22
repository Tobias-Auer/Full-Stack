import os
from zipfile import ZipFile
from datetime import datetime

import requests

import dataBaseOperations


class BackupApi:
    """
    Class for Backup
    """
    def __init__(self, logger=None):
        self.logger = logger

    def makeBackup(self):
        """
        If called, the function will create a backup from the paths defined in "backupPaths"

        :return: Returns False if the Backup failed otherwise returns True
        """
        self.logger.info("Creating backup")
        base_path = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1"
        backupPaths = [r"\logs",
                       r"\world",
                       r"\world_nether",
                       r"\world_the_end",
                       r"\plugins"]
        targetPath = fr"E:\backups_mc\{datetime.now().strftime('%Y-%m-%d %H.%M.%S')}"
        self.logger.debug("base_path: %s", base_path)
        self.logger.debug("backupPaths: %s", backupPaths)
        self.logger.debug("targetPath: %s", targetPath)
        # Create object of ZipFile
        try:
            with ZipFile(f'{targetPath}.zip', 'w') as zip_object:
                # Traverse all files in directory
                for path in backupPaths:
                    print(f"Start to backup: {path}")
                    self.logger.info(f"Start to backup: {path}")
                    path = base_path + path
                    for folder_name, sub_folders, file_names in os.walk(path):
                        print(f"|----Folder: {folder_name}")
                        self.logger.info(f"|----Folder: {folder_name}")
                        for filename in file_names:
                            print(f"|--------File: {filename}")
                            self.logger.info(f"|--------File: {filename}")
                            if filename.endswith(".jar"):
                                print(f"|--------Skip file: {filename}")
                                continue
                            # Create filepath of files in directory
                            file_path = os.path.join(folder_name, filename)
                            # Add files to zip file
                            zip_object.write(file_path, os.path.relpath(file_path, base_path))
                    print(f"Done with {path}")
                    self.logger.info(f"Done with {path}")
        except (Exception,) as e:
            print("[ERROR] Fehler beim Backup:")
            self.logger.error("[ERROR] Fehler beim Backup:")
            print(e)
            return False

        if os.path.exists(f'{targetPath}.zip'):
            print("Backup successful created")
            self.logger.info("Backup successful created")
            return True
        else:
            print("[ERROR] Unknown error, zip is not created properly")
            self.logger.error("[ERROR] Unknown error, zip is not created properly")
            return False

    def doBackupRoutine(self):
        self.logger.info("Backup recognized")
        backupStatus = self.makeBackup()
        self.logger.info("Backup created successfully") if backupStatus else self.logger.error(
            "Failed to create backup")
        return backupStatus


class MixedUtilsApi:
    def __init__(self, logger=None):
        self.logger = logger

    def doShutdownRoutine(self):
        self.logger.info("Shutdown recognized")

        shutdownKeyDeleteStatus = dataBaseOperations.deleteKey("meta", "doAction", "shutdown")
        if shutdownKeyDeleteStatus == True:
            self.logger.debug("Delete Shutdown-Key from db")
        else:
            self.logger.error(shutdownKeyDeleteStatus)

        if dataBaseOperations.checkForKey("meta", "doAction", "backup"):
            backupApi = BackupApi(self.logger)
            backupApi.doBackupRoutine()
            backupKeyDeleteStatus = dataBaseOperations.deleteKey("meta", "doAction", "backup")
            if backupKeyDeleteStatus == True:
                self.logger.debug("Delete Backup-Key from db")
            else:
                self.logger.error(shutdownKeyDeleteStatus)

        else:
            self.logger.info("Backup skipped")

        os.system("shutdown -s")
        self.logger.info("Started shutdown")


class DatabaseApi:
    def __init__(self, logger=None):
        self.logger = logger

    def get_all_uuids_from_db(self):
        unique_uuids = []
        try:
            all_tables = dataBaseOperations.list_all_tables()

            for table in all_tables:
                uuid = str(table[0]).split('~')[0]
                if str(uuid) not in unique_uuids:
                    unique_uuids.append(str(uuid))
        except Exception as e:
            self.logger.error(e)
            if self.logger is None:
                print(e)
        finally:
            return unique_uuids

    def get_user_status(self, user_uuid):
        status = dataBaseOperations.get_player_status(user_uuid)
        if type(status) != str:
            status = "dbError"
        return status

    def check_for_status(self):
        status_list = dataBaseOperations.return_complete_column("status", "status")
        for status in status_list:
            if status[0] is None or "~" not in status[0]:
                print(f"Skipped status: {status}")
                continue
            print("Status:" + str(status))
            status = status[0].split("~")
            str(status[0]).replace("-","")
            print(f"Updating player status for player: {status[0]} to {status[1]}")
            self.__update_player_status(status[0], status[1])
            dataBaseOperations.delete_specific_key("status", "status", f"{status[0]}~{status[1]}")

    @staticmethod
    def __update_player_status(player_uuid, status):
        dataBaseOperations.write_player_status(player_uuid, status)


class MinecraftApi:

    def __init__(self, logger=None):
        self.logger = logger

    def get_username_from_uuid(self, UUID):
        URL = f"https://api.mojang.com/user/profile/{UUID}"
        user_name = None
        try:
            response = requests.get(URL)
            if response.status_code == 200:
                data = response.json()
                user_name = data.get("name")
        except Exception as e:
            self.logger.error(e)
            if self.logger is None:
                print(e)
        finally:
            return user_name

    def get_uuid_from_username(self, USERNAME):
        uuid = None
        URL = f"https://api.mojang.com/users/profiles/minecraft/{USERNAME}"
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


if __name__ == '__main__':
    api = MinecraftApi()
    print(api.get_uuid_from_username("_Tobias4444"))
    print(api.get_username_from_uuid("4ebe5f6fc23143159d60097c48cc6d30"))
    dataApi = DatabaseApi()
    dataApi.get_all_uuids_from_db()
    dataApi.check_for_status()
    print(dataApi.get_user_status("_Tobias4444"))

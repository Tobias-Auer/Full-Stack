import os
from zipfile import ZipFile
from datetime import datetime

import requests

import dataBaseOperations


def makeBackup(logger=None):
    logger.info("Creating backup")
    base_path = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1"
    backupPaths = [r"\logs",
                   r"\world",
                   r"\world_nether",
                   r"\world_the_end",
                   r"\plugins"]
    targetPath = fr"E:\backups_mc\{datetime.now().strftime('%Y-%m-%d %H.%M.%S')}"
    logger.debug("base_path: %s", base_path)
    logger.debug("backupPaths: %s", backupPaths)
    logger.debug("targetPath: %s", targetPath)
    # Create object of ZipFile
    try:
        with ZipFile(f'{targetPath}.zip', 'w') as zip_object:
            # Traverse all files in directory
            for path in backupPaths:
                print(f"Start to backup: {path}")
                logger.info(f"Start to backup: {path}")
                path = base_path + path
                for folder_name, sub_folders, file_names in os.walk(path):
                    print(f"|----Folder: {folder_name}")
                    logger.info(f"|----Folder: {folder_name}")
                    for filename in file_names:
                        print(f"|--------File: {filename}")
                        logger.info(f"|--------File: {filename}")
                        # Create filepath of files in directory
                        file_path = os.path.join(folder_name, filename)
                        # Add files to zip file
                        zip_object.write(file_path, os.path.relpath(file_path, base_path))
                print(f"Done with {path}")
                logger.info(f"Done with {path}")
    except (Exception,) as e:
        print("[ERROR] Fehler beim Backup:")
        logger.error("[ERROR] Fehler beim Backup:")
        print(e)
        return False

    if os.path.exists(f'{targetPath}.zip'):
        print("Backup successful created")
        logger.info("Backup successful created")
        return True
    else:
        print("[ERROR] Unknown error, zip is not created properly")
        logger.error("[ERROR] Unknown error, zip is not created properly")
        return False


def doBackupRoutine(logger):
    logger.info("Backup recognized")
    backupStatus = makeBackup(logger)
    logger.info("Backup created successfully") if backupStatus else logger.error("Failed to create backup")
    return backupStatus


def doShutdownRoutine(logger):
    logger.info("Shutdown recognized")

    shutdownKeyDeleteStatus = dataBaseOperations.deleteKey("meta", "doAction", "shutdown")
    if shutdownKeyDeleteStatus == True:
        logger.debug("Delete Shutdown-Key from db")
    else:
        logger.error(shutdownKeyDeleteStatus)

    if dataBaseOperations.checkForKey("meta", "doAction", "backup"):
        doBackupRoutine(logger)
        backupKeyDeleteStatus = dataBaseOperations.deleteKey("meta", "doAction", "backup")
        if backupKeyDeleteStatus == True:
            logger.debug("Delete Backup-Key from db")
        else:
            logger.error(shutdownKeyDeleteStatus)

    else:
        logger.info("Backup skipped")

    os.system("shutdown -s")
    logger.info("Started shutdown")


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

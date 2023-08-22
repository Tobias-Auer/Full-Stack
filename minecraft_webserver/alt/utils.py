import os
from zipfile import ZipFile
from datetime import datetime

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
                logger.info(f"Start to backup: {path}")
                path = base_path + path
                for folder_name, sub_folders, file_names in os.walk(path):
                    logger.info(f"|----Folder: {folder_name}")
                    for filename in file_names:
                        # Create filepath of files in directory
                        file_path = os.path.join(folder_name, filename)
                        # Add files to zip file
                        zip_object.write(file_path, os.path.relpath(file_path, base_path))
                logger.info(f"Done with {path}")
    except (Exception,) as e:
        logger.error("[ERROR] Fehler beim Backup:")
        logger.error(e)
        return False

    if os.path.exists(f'{targetPath}.zip'):
        logger.info("Backup successful created")
        return True
    else:
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


if __name__ == '__main__':
    import logging
    doShutdownRoutine(logging.getLogger())

import sqlite3
import time
import traceback
from datetime import datetime

import utils

USE_TEST_DB = False


class DatabaseHandler:
    """
    Class for handling various database operations except for player statistic information management (handled in
    "updateDBStats.py").
    """

    def __init__(self, db_file):
        """
        Initialize a DatabaseHandler instance.

        :param db_file: Filepath of the database.
        """
        self.minecraftApi = utils.MinecraftApi()
        self.conn = None
        self.cursor = None
        if db_file == "interface":
            db_file = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\database_webserver\data.db"
        elif db_file == "playerData":
            db_file = r"./player_data.db"
        elif db_file == "prefix":
            db_file = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\database_webserver\prefixes.db"
        else:
            db_file = db_file
        self.__connect(db_file)

    def __connect(self, db_file):
        """
        Connect to the specified database.

        :param db_file: Filepath of the database.
        :return: None
        """
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        """
        Close the database connection and commit pending transactions.

        :return: None
        """
        if self.conn:
            self.conn.commit()
            self.cursor.close()
            self.conn.close()

    def list_all_tables(self):
        """
        Retrieve a list of all table names in the database.

        :return: List of table names (strings).
        """
        query = "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        self.cursor.execute(query)
        queryResult = self.cursor.fetchall()
        return queryResult

    def check_for_key(self, table, column, key):
        """
        Check if a given key exists in the specified table and column.

        :param table: Table name.
        :param column: Column name.
        :param key: Key value to check.
        :return: True if the key exists, False otherwise.
        """
        query = f"SELECT COUNT(*) FROM {table} WHERE {column} = ?"
        params = (key,)
        self.cursor.execute(query, params)
        queryResult = self.cursor.fetchone()[0]
        return queryResult > 0

    def return_specific_key(self, table, column, key_column, key_value):
        """
        Retrieve the value associated with a specific key in the specified table and column.

        :param table: Table name.
        :param column: Column name.
        :param key_column: Column where to search for the key.
        :param key_value: Value of the key to search for.
        :return: The value associated with the key.
        """
        query = f"SELECT [{column}] FROM [{table}] WHERE {key_column} = ?"
        params = (key_value,)
        self.cursor.execute(query, params)
        try:
            queryResult = self.cursor.fetchone()[0]
        except TypeError:
            queryResult = None
        return queryResult

    def return_complete_column(self, table, column):
        """
        Retrieve the complete column specified in the table.

        :param table: Table name.
        :param column: Column name.
        :return: List of all values in the specified column.
        """
        query = f"SELECT [{column}] FROM [{table}]"
        try:
            self.cursor.execute(query)
            queryResult = self.cursor.fetchall()
        except sqlite3.OperationalError as e:
            print("Failed to retrieve complete column: error: {}".format(e))
            queryResult = ["Null", ]
        return queryResult

    def get_player_status(self, player_uuid):
        """
        Retrieve the status of the specified player. Returns "offline" if no player entry is found.

        :param player_uuid: UUID of the player.
        :return: "online"|"offline"
        """
        query = f"""
            SELECT status FROM status WHERE player = ?
        """
        self.cursor.execute(query, (player_uuid.replace("-", ""),))
        try:
            status = self.cursor.fetchone()[0]
        except (Exception,):
            status = "offline"
        return str(status)

    # Writing
    def delete_key(self, table, column, key):
        """
        Delete a key from the database specified by table and column.

        :param table: Table name.
        :param column: Column name.
        :param key: Key to delete.
        :return: True if successful, False if no entry was found, or an error message when an error occurs.
        """
        try:
            query_select = f"SELECT * FROM {table} WHERE {column} = ?"
            params = (key,)
            self.cursor.execute(query_select, params)
            rows_to_delete = self.cursor.fetchall()

            if rows_to_delete:
                with self.conn:
                    query_delete = f"DELETE FROM {table} WHERE {column} = ?"
                    self.cursor.executemany(query_delete, [(key,) for _ in rows_to_delete])

                return True
            else:
                return False
        except Exception as e:
            return str(e)

    def write_player_status(self, uuid, status):
        """
        Write the player status to the given status.

        :param uuid: Player UUID.
        :param status: Status (online|offline).
        :return: None
        """
        uuid = uuid.replace("-", "")
        query_check = """
            SELECT COUNT(*) FROM status WHERE player = ?
        """
        self.cursor.execute(query_check, (uuid,))
        count = self.cursor.fetchone()[0]
        now = datetime.now()
        CURRENT_DATE = now.strftime("%d.%m.%Y")
        if count > 0:
            query_update = """
                UPDATE status SET status = ? WHERE player = ?
            """
            self.cursor.execute(query_update, (status, uuid))
            self.cursor.execute(f"UPDATE cache SET last_seen = ? WHERE UUID = ?",
                                (CURRENT_DATE, uuid))
            print("Status updated for", uuid)
        else:
            query_insert = """
                INSERT INTO status ("player", "status") VALUES (?, ?)
            """
            self.cursor.execute(query_insert, (uuid, status))

            print("New player entry added:", uuid)
        self.conn.commit()

    def insert_or_update_cache(self, uuid):
        """
        Inserts a new entry or updates an existing entry in the 'cache' table.

        If an entry with the provided UUID exists in the 'cache' table, its 'name' and 'timestamp'
        will be updated. If no entry with the provided UUID exists, a new entry will be inserted.

        :param uuid: The UUID of the player.
        :type uuid: str
        :return: None
        """
        # Check if entry exists
        # count = self.check_for_key("cache", "UUID", uuid)
        # CURRENT_TIMESTAMP = int(time.time())
        #
        # now = datetime.now()
        # CURRENT_DATE = now.strftime("%d.%m.%Y")
        print(uuid)
        name = self.minecraftApi.get_username_from_uuid(uuid)
        print(name)
        self.conn.commit()

    def return_table(self, table_name):
        query = f"SELECT * FROM [{table_name}]"
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
        except sqlite3.OperationalError as e:
            print(e)
            results = []
        return results

    def return_specific_values_with_filter(self, table, search_column, target_column, filter_list):
        """
        Retrieve values from a target column where the search column matches a LIKE statement with a filter list.

        :param table: Table name.
        :param search_column: Column name where to search after the filter.
        :param target_column: Target column name.
        :param filter_list: List of filter values.
        :return: List of values in the specified target column matching any of the filter values.
        """
        chunk_size = 100  # Define the maximum number of filter values per query to avoid expression tree too long error
        results = []

        for i in range(0, len(filter_list), chunk_size):
            chunk = filter_list[i:i + chunk_size]
            like_conditions = ' OR '.join([f"[{search_column}] LIKE ?" for _ in chunk])
            query = f"SELECT [{target_column}] FROM [{table}] WHERE {like_conditions}"

            try:
                self.cursor.execute(query, tuple(f"%{filter_value}%" for filter_value in chunk))
                results.extend([row[0] for row in self.cursor.fetchall()])
            except sqlite3.OperationalError as e:
                print(f"\nError:\n{e}\n")
                results.extend(["null"] * len(chunk))
        return results

    def write_specific_value(self, table, search_column, search_value, target_column, value):
        try:
            # SQL statement to update the target_column with the new value
            update_query = f"UPDATE {table} SET {target_column} = ? WHERE {search_column} = ?"
            self.cursor.execute(update_query, (value, search_value))
            self.conn.commit()
            print("Updated table successfully")
        except sqlite3.Error as e:
            print("Error:", e)

    def create_login_entry(self, uuid, secret_pin):
        if self.check_for_login_entry(uuid):
            self.delete_login_entry(uuid)
        CURRENT_TIMESTAMP = int(time.time())
        query = "INSERT INTO login (uuid, secret_pin, timestamp) VALUES (?, ?, ?)"
        self.cursor.execute(query, (uuid, secret_pin, CURRENT_TIMESTAMP))
        self.conn.commit()

    def check_for_login_entry(self, uuid):
        existing_uuid_query = "SELECT COUNT(*) FROM login WHERE uuid = ?"
        self.cursor.execute(existing_uuid_query, (uuid,))
        count = self.cursor.fetchone()[0]
        if count == 0:
            return False
        CURRENT_TIMESTAMP = int(time.time())

        timestamp_query = "SELECT timestamp FROM login WHERE uuid = ?"
        self.cursor.execute(timestamp_query, (uuid,))
        OLD_TIMESTAMP = int(self.cursor.fetchone()[0])
        time_difference = CURRENT_TIMESTAMP - OLD_TIMESTAMP
        if time_difference > 300:
            self.delete_login_entry(uuid)
            return False
        return True

    def get_login_entry(self, uuid):
        query = "SELECT secret_pin FROM login WHERE uuid = ?"
        self.cursor.execute(query, (uuid,))
        secret_pin = self.cursor.fetchone()[0]
        return secret_pin

    def delete_login_entry(self, uuid):
        delete_query = "DELETE FROM login WHERE uuid = ?"
        self.cursor.execute(delete_query, (uuid,))
        self.conn.commit()

    def is_entry_exists(self, uuid_str, prefix_str):
        self.cursor.execute("SELECT * FROM main WHERE uuid=? AND prefix COLLATE NOCASE=?", (uuid_str, prefix_str))
        return self.cursor.fetchone() is not None

    def write_prefix(self, uuid, prefixName, color, password, clearMemberList=True):
        return_value = "error:error_not_defined"
        prefix = f"{color}[{prefixName}]"
        try:
            if self.is_entry_exists(uuid, prefix):
                print("if block")
                return_value = "error:existing_entry_found"
            else:
                # TODO: if the prefix is already set, add an option to clear the member list.
                if clearMemberList:  # must run on the first time the user defines a prefix
                    self.cursor.execute("INSERT OR REPLACE INTO main (uuid, prefix, members) VALUES (?, ?, ?)",
                                        (uuid, prefix, uuid + ","))  # replaces all values including members
                else:
                    self.cursor.execute("INSERT OR REPLACE INTO main (uuid, prefix) VALUES (?, ?)",
                                        (uuid, prefix))

                if password != "":
                    self.cursor.execute("UPDATE main SET (password)=? WHERE uuid=?", (password, uuid))
                print("entered values successfully")
                return_value = "success:success"
                self.conn.commit()

        except sqlite3.IntegrityError as e:
            print("exception")
            print(f"Fehler beim Einfügen der Daten: {e}")
            return_value = "error:db:" + str(e)
        except Exception as e:
            return_value = "error:db:" + str(e) + " details: " + str(traceback.format_exc())
        finally:
            print("finally")
            return return_value

    def get_pref(self, uuid):
        try:
            # Define the SQL query to check for the existence of a prefix for a given UUID
            query = "SELECT prefix FROM main WHERE uuid = ?"
            self.cursor.execute(query, (uuid,))
            result = self.cursor.fetchone()

            if result:
                return [True, result[0]]
            else:
                return [False, ""]

        except sqlite3.Error as e:
            print(f"Error: {e}")
            return [False, ""]

    def get_all_pref(self):
        try:
            query = "SELECT prefix FROM main"
            self.cursor.execute(query)
            prefixes = self.cursor.fetchall()
            query = "SELECT uuid FROM main"
            self.cursor.execute(query)
            uuids = self.cursor.fetchall()
            result = []
            for i in range(len(prefixes)):
                result.append([prefixes[i][0], uuids[i][0]])
            return result
        except sqlite3.Error as e:
            print(f"Error: {e}")
            return None

    def check_for_prefix(self, prefix, password=None, require_pwd=False):
        require_pwd_message = False
        try:
            query = "SELECT COUNT(*) FROM main WHERE prefix = ?"
            self.cursor.execute(query, (prefix,))
            prefix_count = self.cursor.fetchone()[0]
            print("DER PREFIX COUNT: %d" % prefix_count)
            query = "SELECT password FROM main WHERE prefix = ?"
            self.cursor.execute(query, (prefix,))
            try:
                db_password = self.cursor.fetchone()[0]
                print("PWD"+str(password))
            except (Exception,):
                db_password = None
                print("PWD" + str(password))
            if not require_pwd:
                if db_password is not None:
                    require_pwd_message = True
            return [prefix_count > 0 and (password == db_password or not require_pwd), require_pwd_message]
        except (Exception,) as e:
            print(f"Error: {e}")
            return False

    def apply_prefix(self, uuid, requested_prefix):
        print(uuid, requested_prefix)
        try:
            # find existing prefix
            query = "SELECT prefix FROM main WHERE members LIKE ?"
            self.cursor.execute(query, (f"%{uuid}%",))
            own_prefix_name = self.cursor.fetchone()[0]
            print(f"der bisherige prefix lautet: {own_prefix_name}")
            if own_prefix_name == requested_prefix:
                return [False, "this prefix is already assigned to you"]

            # delete existing prefix
            query = "UPDATE main SET members = REPLACE(members, ?, '') WHERE prefix = ?"
            self.cursor.execute(query, (f"{uuid},", own_prefix_name))
            self.conn.commit()

            # add to new prefix
            query = "UPDATE main SET members = members || ? WHERE prefix = ?"
            self.cursor.execute(query, (f"{uuid},", requested_prefix))
            self.conn.commit()
            return [True, ]
        except Exception as e:
            print(f"Error: {e}")
            return [False, str(e)]

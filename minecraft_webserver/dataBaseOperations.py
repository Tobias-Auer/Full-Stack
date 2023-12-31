import ast
import re
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
        elif db_file == "ban_interface":
            db_file = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\database_webserver\banned.db"
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

    def get_player_status(self, player_uuid, return_all=False):
        """
        Retrieve the status of the specified player. Returns "offline" if no player entry is found.

        :param return_all: if the flag is set, the function returns the count of all online players
        :param player_uuid: UUID of the player.
        :return: "online"|"offline" or -1 in case of an error during return_all=True
        """
        if not return_all:
            query = f"SELECT status FROM status WHERE player = ?"
            self.cursor.execute(query, (player_uuid.replace("-", ""),))
        else:
            query = f"SELECT COUNT(*) FROM status WHERE status = 'online'"
            self.cursor.execute(query)
        try:
            status = self.cursor.fetchone()[0]
        except (Exception,):
            status = "offline" if not return_all else -1
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

        CURRENT_TIMESTAMP = int(time.time())

        now = datetime.now()
        CURRENT_DATE = now.strftime("%d.%m.%Y")
        name = self.minecraftApi.get_username_from_uuid(uuid)

        # Check if entry exists
        query = "SELECT COUNT(*) FROM cache WHERE uuid = ?"
        self.cursor.execute(query, (uuid,))

        try:
            count = self.cursor.fetchone()[0]
        except Exception:
            count = 0

        if count > 0:
            # Update existing entry
            self.cursor.execute(f"UPDATE cache SET name = ?, timestamp = ? WHERE UUID = ?",
                                (name, CURRENT_TIMESTAMP, uuid))
        else:
            # Insert new entry
            self.cursor.execute(
                "INSERT INTO cache (UUID, name, timestamp, first_seen, last_seen, access_level, banned) VALUES "
                "(?, ?, ?, ?, ?, ?, ?)",
                (uuid, name, CURRENT_TIMESTAMP, CURRENT_DATE, CURRENT_DATE, 2, "False"))
        self.conn.commit()

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

    def does_entry_exists(self, uuid, prefix, prefixName):
        query = "SELECT prefix FROM main WHERE prefix like ?"
        self.cursor.execute(query, ('%' + prefixName + '%',))
        try:
            already_assigned_prefix = self.cursor.fetchone()[0]
        except Exception:
            already_assigned_prefix = ""
        already_there = already_assigned_prefix != ""
        if not already_there:
            return False
        query = "SELECT prefix FROM main WHERE uuid=?"  # check whether the owner itself overwrites his own color
        self.cursor.execute(query, (uuid,))
        try:
            prefix_from_owner = self.cursor.fetchone()[0]
        except Exception:
            prefix_from_owner = ""

        owner_itself = prefix_from_owner == already_assigned_prefix
        if owner_itself:
            return False
        else:
            already_assigned_prefix_substring = already_assigned_prefix.split("[")[1][0:-1]
            if already_assigned_prefix_substring.lower() == prefixName.lower():
                return True
            return False

    def write_prefix(self, uuid, prefixName, color, password):
        prefix = f"{color}[{prefixName}]"
        try:
            if self.does_entry_exists(uuid, prefix, prefixName):
                return "error:existing_entry_found"
            else:
                # check for existing entry
                query = "SELECT COUNT(*) FROM main WHERE uuid = ?"
                self.cursor.execute(query, (uuid,))
                print("DEBUG: get count")
                try:
                    count = self.cursor.fetchone()[0]
                    print(f"DEBUG: count: {count}")
                except Exception:
                    count = 1
                if count == 0:  # no entry found
                    query = "INSERT INTO main (uuid, prefix, password, members) VALUES (?, ?, ?, ?)"
                    self.cursor.execute(query, (uuid, prefix, password, uuid + ","))
                    return "success:success"
                # only for updating not for new entries!!!
                self.cursor.execute("UPDATE main SET prefix=?, password=? WHERE uuid=?", (prefix, password, uuid))
                print("entered values successfully")
                self.conn.commit()
                return "success:success"

        except sqlite3.IntegrityError as e:
            print("exception")
            print(f"Fehler beim Einfügen der Daten: {e}")
            return "error:db:" + str(e) + " details: " + str(
                traceback.format_exc())  # should be removed in future production code bc of potential security issues(?)
        except Exception as e:
            return "error:db:" + str(e) + " details: " + str(
                traceback.format_exc())  # should be removed in future production code bc of potential security issues(?)

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
                print("PWD" + str(password))
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

    def get_banned_status(self, uuid):
        try:
            query = "SELECT banned FROM cache where UUID = ?"
            self.cursor.execute(query, (uuid,))
            banned_status = self.cursor.fetchone()[0]
            return banned_status
        except (Exception,) as e:
            print(f"Error: {e}")
            return False

    def get_banned_dates(self, uuid):
        try:
            query = "SELECT banned_details FROM cache where UUID = ?"
            self.cursor.execute(query, (uuid,))
            banned_details = self.cursor.fetchone()[0]
            banned_details = ast.literal_eval(banned_details)
            return banned_details[2], banned_details[3]
        except (Exception,) as e:
            print(f"Error: {e}")
            return False

    def get_access_level(self, uuid):
        query = "SELECT access_level FROM cache where uuid = ?"
        try:
            self.cursor.execute(query, (uuid,))
            return self.cursor.fetchone()[0]
        except (Exception,) as e:
            print(f"Error: {e}")
            return 99

    def change_access_level(self, uuid, new_access_level):
        query = "UPDATE cache SET access_level = ? WHERE UUID = ?"
        try:
            self.cursor.execute(query, (int(new_access_level), uuid))
            self.conn.commit()
            return ["True", ""]
        except (Exception,) as e:
            print(e)
            return ["False", e]

    def get_ban_entries(self):
        query = "SELECT uuid FROM main"
        query2 = "SELECT admin, reason, start, end FROM main WHERE REPLACE(uuid, '-', '') = ?"
        new_banned_uuids = []
        try:
            self.cursor.execute(query)
            all_uuids = self.cursor.fetchall()
            for i in all_uuids:
                uuid = i[0].replace("-", "")

                self.cursor.execute(query2, (uuid,))
                result = self.cursor.fetchone()
                new_banned_uuids.append([uuid, result])
        except Exception as e:
            print(e)
        return new_banned_uuids

    def toggle_ban_state(self, uuids, state, single_flag=False):  # single_flag is used when not every banned uuid is provided
        clean_uuid_list_to_ban = []

        query = "UPDATE cache SET banned = ?, banned_details = ? WHERE uuid = ?"
        for uuid in uuids:
            print(f"{state}ing uuid: {uuid[0]} with reasons: {uuid[1]}")
            self.cursor.execute(query, (state, str(list(uuid[1])), uuid[0]))
            clean_uuid_list_to_ban.append(uuid[0])
        self.conn.commit()

        if not single_flag:
            query = "SELECT UUID FROM cache WHERE banned = 'True'"
            self.cursor.execute(query)
            already_banned_uuids = self.cursor.fetchall()
            for uuid in already_banned_uuids:
                if uuid[0] not in clean_uuid_list_to_ban:
                    query = "UPDATE cache SET banned = 'False', banned_details = '' WHERE uuid = ?"
                    self.cursor.execute(query, (uuid[0],))
            self.conn.commit()

    def convert_trimmed_to_full(self, trimmed_uuid):
        # Use a regular expression to insert hyphens at the correct positions
        full_uuid = re.sub(r'(\w{8})(\w{4})(\w{4})(\w{4})(\w{12})', r'\1-\2-\3-\4-\5', trimmed_uuid)
        return full_uuid

    def ban_player(self, uuid, details=None):
        if details is None:
            details = ['4ebe5f6f-c231-4315-9d60-097c48cc6d30', 'Banned by website! More options soon!', '22-11-2023 19:27:31',
                       '22-11-9999 00:00:00']  # good enough until the frontend is updated
        # self.toggle_ban_state([[uuid, details]], "True", single_flag=True)  # not necessary, but maybe i should use it

        db_handler = DatabaseHandler("ban_interface")
        query = "INSERT INTO status (webserver_changed_sth) VALUES (?)"
        uuid = self.convert_trimmed_to_full(uuid)
        query_argument = f"add~{uuid},{details[0]},{details[1]},{details[2]},{details[3]}"
        db_handler.cursor.execute(query, (query_argument,))
        db_handler.disconnect()

    def unban_player(self, uuid):
        # self.toggle_ban_state([[uuid, ""]], "False", single_flag=True)  # not necessary, but maybe i should use it
        db_handler = DatabaseHandler("ban_interface")
        query = "INSERT INTO status (webserver_changed_sth) VALUES (?)"
        uuid = self.convert_trimmed_to_full(uuid)
        query_argument = f"remove~{uuid}"
        db_handler.cursor.execute(query, (query_argument,))
        db_handler.disconnect()

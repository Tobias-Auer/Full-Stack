# TODO: Convert this file into class

import sqlite3

USE_TEST_DB = False


class DatabaseHandler:
    """
    Class for handling various database operations except for player statistic information management (handled in "updateDBStats.py").
    """

    def __init__(self, db_file):
        """
        Initialize a DatabaseHandler instance.

        :param db_file: Filepath of the database.
        """
        self.conn = None
        self.cursor = None
        if db_file == "interface":
            db_file = r"C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\database_webserver\data.db"
        elif db_file == "playerData":
            db_file = r"./player_data.db"
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

    def return_specific_key(self, table, column, key):
        """
        Retrieve the value associated with a specific key in the specified table and column.

        :param table: Table name.
        :param column: Column name.
        :param key: Key value to search for.
        :return: The value associated with the key.
        """
        query = f"SELECT value FROM [{table}] WHERE {column} = ?"
        params = (key,)
        self.cursor.execute(query, params)
        queryResult = self.cursor.fetchone()[0]
        return queryResult

    def return_complete_column(self, table, column):
        """
        Retrieve the complete column specified in the table.

        :param table: Table name.
        :param column: Column name.
        :return: List of all values in the specified column.
        """
        query = f"SELECT [{column}] FROM [{table}]"
        self.cursor.execute(query)
        queryResult = self.cursor.fetchall()
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

        if count > 0:
            query_update = """
                UPDATE status SET status = ? WHERE player = ?
            """
            self.cursor.execute(query_update, (status, uuid))
            print("Status updated for", uuid)
        else:
            query_insert = """
                INSERT INTO status ("player", "status") VALUES (?, ?)
            """
            self.cursor.execute(query_insert, (uuid, status))
            print("New player entry added:", uuid)
        self.conn.commit()
# if __name__ == '__main__':
#     print(return_specific_key("36c5cd1361f444f199870390f20c9ea2~minecraft:custom", "key", "minecraft:jump"))
#     print(return_complete_column("status", "status"))
#     write_player_status("_Tobias4444", "Online")
# def init(player_data_db=False):
#     if player_data_db:
#         print("Connect to player data db")
#         conn = sqlite3.connect(fr'./player_data.db')
#     else:
#         conn = sqlite3.connect(r'C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\databse_webserver\data.db')
#     if USE_TEST_DB:
#         print("Connect to minecraft interface")
#         conn = sqlite3.connect(r'./data.db')
#
#     cursor = conn.cursor()
#     return conn, cursor

# def kill(conn, cursor):
#     conn.commit()
#     cursor.close()
#     conn.close()

# def deleteKey(self, table, field, key):
#     try:
#         recursionCounter = 0
#         while self.checkForKey(table, field, key):
#             if recursionCounter >= 100:
#                 return "recursionLimit reached"
#             recursionCounter += 1
#
#             query = f"DELETE FROM {table} WHERE {field} = ?"
#             params = (key,)
#             self.cursor.execute(query, params)
#             self.conn.commit()
#         return True
#     except Exception as e:
#         return str(e)

    # def delete_specific_key(self, table, column, field):
    #     """
    #
    #     :param table: Table name
    #     :param column: Column name
    #     :param field:
    #     :return:
    #     """
    #     query = f"DELETE FROM [{table}] WHERE {column} = \"{field}\""
    #     print(query)
    #     self.cursor.execute(query)
    #     self.conn.commit()

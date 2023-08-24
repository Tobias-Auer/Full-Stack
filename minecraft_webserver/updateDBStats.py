# TODO: Mainloop to call these functions regularly
import sqlite3
import os
import json


class StatisticsUpdater:
    """
    Class for handling various database operations but only for player statistics.
    """

    def __init__(self, db_file):
        """
        Initialize a DatabaseHandler instance.

        :param db_file: Filepath of the database.
        """
        self.conn = None
        self.cursor = None
        self.connect(db_file)

    def connect(self, db_file):
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

    # create
    def __create_game_specific_table(self, table_name):
        """
        Method to create a table in the database with the following format:
        key(Str) - value(Int)

        To update the tables created by this method call "update_game_specific_tables(<json file>)"

        This method is used to store the game specific statistics from a player. The data input should come from the
        game player statistics file For each player it must be called 9 times (broken,crafted,custom,dropped,killed,
        killed_by,mined,picked_up,used) which is automatically done by "update_game_specific_tables_from_file(<json
        file>)" when a table is missing


        :param table_name: The name of the table
        :return: None
        """
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                "key" VARCHAR(64) PRIMARY KEY,
                "value" INTEGER
            )
        """
        self.cursor.execute(create_table_query)

    def create_player_info_table(self, table_name):
        """
        Method to create a table in the database with the following format:
        username(Str) - last_seen(Str) - banned(bool) - ban_count(int) - ban_reasons(Str)
        This method must be called once per player and stores general metadata but not the username.
        This is cached in the cache table

        :param table_name: The name of the table
        :return: None
        """
        create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        "username" VARCHAR(64) PRIMARY KEY,
                        "last_seen" VARCHAR(16),
                        "banned" BOOLEAN,
                        "ban_count" INTEGER,
                        "ban_reasons" VARCHAR(64)
                    )
                """

        self.cursor.execute(create_table_query)

    # update
    def update_game_specific_tables_from_file(self, filename):
        """
        Updates the game specific tables created in "create_game_specific_table()" Takes the statistics json file as
        parameter, get the uuid from the file name and updates all statistic tables from the player
        :param filename: statistics json file
        :return: None
        """
        uuid = os.path.splitext(filename)[0].replace("-", "").split("\\")[-1]
        with open(filename, 'r') as f:
            data = json.load(f)
            # self.__update_game_specific_tables(uuid, data)
        for key, action in data["stats"].items():
            all_keys = list(action.keys())
            all_values = list(action.values())
            table_name_unescaped = uuid + "~" + key
            table_name = "[" + table_name_unescaped + "]"

            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name_unescaped}'")
            existing_table = self.cursor.fetchone()
            if existing_table is not None:
                print(f"Updating {table_name}")
                self.update_or_insert_game_data(table_name, all_keys, all_values)
            else:
                print(f"Creating {table_name}")
                self.__create_game_specific_table(table_name)
                self.update_or_insert_game_data(table_name, all_keys, all_values)

    def update_or_insert_game_data(self, table_name, keys, values):
        """
        Updates or inserts game specific data into the database.
        Only for players statistics
        :param table_name: Table name
        :param keys: keys to insert/update
        :param values: values to insert/update
        :return: None
        """
        for key, value in zip(keys, values):
            if self.entry_exists(table_name, key):
                self.update_game_data(table_name, key, value)
            else:
                self.insert_game_data(table_name, key, value)
        self.conn.commit()

    def entry_exists(self, table_name, key):
        """
        Checks if an entry with the given key exists in the table.
        :param table_name: Table name
        :param key: Key to check
        :return: True if entry exists, False otherwise
        """
        check_query = f"""
            SELECT COUNT(*) 
            FROM '{table_name}'
            WHERE "key" = ?
        """
        self.cursor.execute(check_query, (key,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def update_game_data(self, table_name, key, value):
        """
        Updates game specific data in the database.
        Only for players statistics
        :param table_name: Table name
        :param key: key to update
        :param value: value to update
        :return: None
        """
        update_query = f"""
            UPDATE '{table_name}'
            SET "value" = ?
            WHERE "key" = ?
        """
        self.cursor.execute(update_query, (value, key))
        self.conn.commit()

    def insert_game_data(self, table_name, key, value):
        """
        Inserts game specific data into the database.
        Only for players statistics
        :param table_name: Table name
        :param key: key to insert
        :param value: value to insert
        :return: None
        """
        insert_query = f"""
            INSERT INTO '{table_name}' ("key", "value")
            VALUES (?, ?)
        """
        self.cursor.execute(insert_query, (key, value))
        self.conn.commit()

    # def insert_player_specific_data(self, table_name, column_names, values):
    #     """
    #     Inserts metadata for the player in the player meta table created in "create_player_info_table()"
    #
    #     Idk what I was thinking back then when i was creating this function, so I have no clue what it is doing xD
    #
    #     WILL BE REWRITTEN WHEN NEEDED!
    #     NOT FOR READY FOR USE!
    #
    #     :param table_name:
    #     :param column_names:
    #     :param values:
    #     :return:
    #     """
    #     column_names_string = ", ".join([f'"{name}"' for name in column_names])
    #     value_placeholders = ", ".join(["?" for _ in column_names])
    #     insert_query = f"""
    #         INSERT INTO {table_name} ({column_names_string})
    #         VALUES ({value_placeholders})
    #     """
    #     default_values = [None if value is None else value for value in values]
    #     self.cursor.execute(insert_query, default_values)

    # def __update_game_specific_tables(self, UUID, data):
    #     for key, action in data["stats"].items():
    #         all_keys = list(action.keys())
    #         all_values = list(action.values())
    #         table_name_unescaped = UUID + "~" + key
    #         table_name = "[" + table_name_unescaped + "]"
    #
    #         self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name_unescaped}'")
    #         existing_table = self.cursor.fetchone()
    #         if existing_table is not None:
    #             print(f"Updating {table_name}")
    #             self.update_game_specific_data(table_name, all_keys, all_values)
    #         else:
    #             print(f"Creating {table_name}")
    #             self.create_game_specific_table(table_name)
    #             self.insert_game_specific_data(table_name, all_keys, all_values)

    def update_player_specific_tables(self, UUID, data):
        ...

    def update_player_specific_tables_from_file(self):
        ...


if __name__ == '__main__':
    ...
    # directory = './sampleData'
    # files = os.listdir(directory)
    # statistic_updater = StatisticsUpdater("main.db")
    # # statistic_updater.create_player_info_table("SAMPLE_UUID")
    # # statistic_updater.insert_player_specific_data("SAMPLE_UUID", ["username", "banned"], ["_Tobias", "TRUE"])
    # for file in files:
    #     if file.endswith('.json'):
    #         filepath = os.path.join(directory, file)
    #         statistic_updater.update_database_from_file(filepath)
    # statistic_updater.disconnect()

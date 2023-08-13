import sqlite3
import os
import json


class StatisticsUpdater:
    def __init__(self, db_file):
        self.conn = None
        self.cursor = None
        self.connect(db_file)

    def connect(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def create_game_specific_table(self, table_name):
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                "key" VARCHAR(64) PRIMARY KEY,
                "value" INTEGER
            )
        """
        self.cursor.execute(create_table_query)

    def create_player_info_table(self, table_name):
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

    def update_game_specific_data(self, table_name, keys, values):
        for key, value in zip(keys, values):
            update_query = f"""
                UPDATE {table_name}
                SET "value" = {value}
                WHERE "key" = "{key}"
            """
            self.cursor.execute(update_query)

    def insert_game_specific_data(self, table_name, keys, values):
        for key, value in zip(keys, values):
            insert_query = f"""
                INSERT INTO {table_name} ("key", "value")
                VALUES ("{key}", {value})
            """
            self.cursor.execute(insert_query)

    def insert_player_specific_data(self, table_name, column_names, values):
        column_names_string = ", ".join([f'"{name}"' for name in column_names])
        value_placeholders = ", ".join(["?" for _ in column_names])
        insert_query = f"""
            INSERT INTO {table_name} ({column_names_string})
            VALUES ({value_placeholders})
        """
        default_values = [None if value is None else value for value in values]
        self.cursor.execute(insert_query, default_values)

    def update_game_specific_tables(self, UUID, data):
        for key, action in data["stats"].items():
            all_keys = list(action.keys())
            all_values = list(action.values())
            table_name_unescaped = UUID + "~" + key
            table_name = "[" + table_name_unescaped + "]"

            self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name_unescaped}'")
            existing_table = self.cursor.fetchone()
            if existing_table is not None:
                print(f"Updating {table_name}")
                self.update_game_specific_data(table_name, all_keys, all_values)
            else:
                print(f"Creating {table_name}")
                self.create_game_specific_table(table_name)
                self.insert_game_specific_data(table_name, all_keys, all_values)

    def update_player_specific_tables(self, UUID, data):
        ...

    def update_game_specific_tables_from_file(self, filename):
        uuid = os.path.splitext(filename)[0].replace("-", "").split("\\")[-1]
        with open(filename, 'r') as f:
            data = json.load(f)
            self.update_game_specific_tables(uuid, data)

    def update_player_specific_tables_from_file(self):
        ...


if __name__ == '__main__':
    directory = './sampleData'
    files = os.listdir(directory)
    statistic_updater = StatisticsUpdater("main.db")
    # statistic_updater.create_player_info_table("SAMPLE_UUID")
    # statistic_updater.insert_player_specific_data("SAMPLE_UUID", ["username", "banned"], ["_Tobias", "TRUE"])
    for file in files:
        if file.endswith('.json'):
            filepath = os.path.join(directory, file)
            statistic_updater.update_database_from_file(filepath)
    statistic_updater.disconnect()

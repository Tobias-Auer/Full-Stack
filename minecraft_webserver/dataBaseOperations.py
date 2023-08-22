# TODO: Convert this file into class

import sqlite3

USE_TEST_DB = False


def init(player_data_db=False):
    if player_data_db:
        print("Connect to player data db")
        conn = sqlite3.connect(fr'./player_data.db')
    else:
        conn = sqlite3.connect(r'C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\databse_webserver\data.db') 
    if USE_TEST_DB:
        print("Connect to minecraft interface")
        conn = sqlite3.connect(r'./data.db')
    
    cursor = conn.cursor()
    return conn, cursor


def kill(conn, cursor):
    conn.commit()
    cursor.close()
    conn.close()


def list_all_tables():
    conn, cursor = init(True)
    query = "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    cursor.execute(query)
    queryResult = cursor.fetchall()
    print(queryResult)
    kill(conn, cursor)
    return queryResult


def checkForKey(table, field, key):
    conn, cursor = init()
    query = f"SELECT COUNT(*) FROM {table} WHERE {field} = ?"
    params = (key,)
    cursor.execute(query, params)
    queryResult = cursor.fetchone()[0]
    kill(conn, cursor)
    return True if queryResult > 0 else False


def deleteKey(table, field, key):
    try:
        recursionCounter = 0
        while checkForKey(table, field, key):
            if recursionCounter >= 100:
                return "recursionLimit reached"
            recursionCounter += 1

            conn, cursor = init()
            query = f"DELETE FROM {table} WHERE {field} = ?"
            params = (key,)
            cursor.execute(query, params)
            conn.commit()
            kill(conn, cursor)
        return True
    except Exception as e:
        return str(e)


def return_specific_key(table, column, field):
    conn, cursor = init(True)
    query = f"SELECT value FROM [{table}] WHERE {column} = \"{field}\""
    cursor.execute(query)
    queryResult = cursor.fetchone()[0]
    kill(conn, cursor)
    return queryResult


def delete_specific_key(table, column, field):
    conn, cursor = init()
    query = f"DELETE FROM [{table}] WHERE {column} = \"{field}\""
    print(query)
    cursor.execute(query)
    kill(conn, cursor)


def return_complete_column(table, column):
    conn, cursor = init()
    query = f"SELECT [{column}] FROM [{table}]"
    cursor.execute(query)
    queryResult = cursor.fetchall()
    kill(conn, cursor)
    return queryResult


def write_player_status(player_name, status):
    conn, cursor = init(True)
    query_check = """
        SELECT COUNT(*) FROM status WHERE player = ?
    """
    cursor.execute(query_check, (player_name.replace("-",""),))
    count = cursor.fetchone()[0]

    if count > 0:
        query_update = """
            UPDATE status SET status = ? WHERE player = ?
        """
        cursor.execute(query_update, (status, player_name.replace("-","")))
        print("Status updated for", player_name.replace("-",""))
    else:
        query_insert = """
            INSERT INTO status ("player", "status") VALUES (?, ?)
        """
        cursor.execute(query_insert, (player_name.replace("-",""), status))
        print("New player entry added:", player_name.replace("-",""))

    kill(conn, cursor)


def get_player_status(player_uuid):
    conn, cursor = init(True)
    query = f"""
        SELECT status FROM status WHERE player = ?
    """
    cursor.execute(query, (player_uuid.replace("-",""), ))
    print("Query: " + query)
    try:
        status = cursor.fetchone()[0]
    except:
        status = None
    print(f"Status: {status}")
    kill(conn, cursor)
    return str(status)


if __name__ == '__main__':
    print(return_specific_key("36c5cd1361f444f199870390f20c9ea2~minecraft:custom", "key", "minecraft:jump"))
    print(return_complete_column("status", "status"))
    write_player_status("_Tobias4444", "Online")

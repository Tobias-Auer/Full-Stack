import sqlite3

USE_TEST_DB = True


def init(player_data_db=False):
    if player_data_db:
        conn = sqlite3.connect(fr'./player_data.db')
    elif USE_TEST_DB:
        conn = sqlite3.connect(r'./data.db')
    else:
        conn = sqlite3.connect(r'C:\Users\balus\OneDrive\Desktop\mc-docker-1.20.1\databse_webserver\data.db')
    cursor = conn.cursor()
    return conn, cursor


def kill(conn, cursor):
    cursor.close()
    conn.close()


def list_all_tables():
    conn, cursor = init(True)
    query = "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    cursor.execute(query)
    queryResult = cursor.fetchall()
    print(queryResult)
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
            recursionCounter += 1
            if recursionCounter >= 50:
                return "recursionCounter reached"
            conn, cursor = init()
            query = f"DELETE FROM {table} WHERE {field} = ?"
            params = (key,)
            cursor.execute(query, params)
            conn.commit()
            kill(conn, cursor)
        return True
    except Exception as e:
        return str(e)

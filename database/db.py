import sqlite3

DB_NAME = "pick_by_light.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn
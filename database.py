# database.py
import sqlite3

def create_connection():
    conn = sqlite3.connect('diet_planner.db')
    return conn

def create_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        api_key TEXT
                    )''')
    conn.commit()
    conn.close()

create_table()

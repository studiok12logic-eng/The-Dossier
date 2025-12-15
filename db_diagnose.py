
import sqlite3
import os

DB_PATH = 'db.sqlite3'

def inspect_table(table_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"--- TABLE: {table_name} ---")
        for col in columns:
            print(f"Col: {col[1]} (Type: {col[2]})")
        conn.close()
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

if __name__ == "__main__":
    inspect_table('intelligence_timelineitem')
    inspect_table('intelligence_question')

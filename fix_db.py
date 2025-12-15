
import sqlite3
import os

DB_PATH = 'db.sqlite3'

def fix_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        print("Adding question_id column...")
        cursor.execute("ALTER TABLE intelligence_timelineitem ADD COLUMN question_id INTEGER REFERENCES intelligence_question(id)")
        conn.commit()
        print("Success.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_db()

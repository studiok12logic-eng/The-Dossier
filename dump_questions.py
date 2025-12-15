
import sqlite3
import os

DB_PATH = 'db.sqlite3'

def dump_questions():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, answer_type, choices FROM intelligence_question")
        rows = cursor.fetchall()
        print(f"--- Questions ({len(rows)}) ---")
        for r in rows:
            print(f"ID: {r[0]}, Title: {r[1]}, Type: {r[2]}, Choices: {r[3]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_questions()

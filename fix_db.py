
import sqlite3
import os

DB_PATH = 'db.sqlite3'

def fix_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing columns in intelligence_timelineitem
    cursor.execute("PRAGMA table_info(intelligence_timelineitem)")
    columns = [r[1] for r in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Columns to ensure
    cols_to_add = [
        ('question_id', 'INTEGER REFERENCES intelligence_question(id)'),
        ('question_text', 'VARCHAR(255)'),
        ('question_answer', 'TEXT'),
        ('question_category', 'VARCHAR(100)'),
        ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
    ]
    
    for col_name, col_def in cols_to_add:
        if col_name not in columns:
            print(f"Adding missing column: {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE intelligence_timelineitem ADD COLUMN {col_name} {col_def}")
                conn.commit()
                print("  -> Done.")
            except Exception as e:
                print(f"  -> Error: {e}")
        else:
            print(f"Column {col_name} exists - skipping.")

    conn.close()

if __name__ == "__main__":
    fix_db()

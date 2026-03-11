import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('academic_assistant.db')
        cursor = conn.cursor()
        cursor.execute('ALTER TABLE attendance ADD COLUMN hours INTEGER DEFAULT 1')
        conn.commit()
        print("Column 'hours' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Migration error (might already exist): {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()

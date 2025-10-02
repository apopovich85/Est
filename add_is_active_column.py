import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# Add is_active column to projects table (default to TRUE for existing projects)
try:
    cursor.execute('ALTER TABLE projects ADD COLUMN is_active BOOLEAN DEFAULT 1')
    print("Added is_active column to projects table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column is_active already exists")
    else:
        raise

conn.commit()
conn.close()
print("Migration complete")

"""
Add revision and remarks fields to projects table
"""
import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# Add revision column to projects table
try:
    cursor.execute('ALTER TABLE projects ADD COLUMN revision VARCHAR(50) DEFAULT ""')
    print("Added revision column to projects table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column revision already exists")
    else:
        raise

# Add remarks column to projects table
try:
    cursor.execute('ALTER TABLE projects ADD COLUMN remarks TEXT DEFAULT ""')
    print("Added remarks column to projects table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column remarks already exists")
    else:
        raise

conn.commit()
conn.close()
print("Migration complete")

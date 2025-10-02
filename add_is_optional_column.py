import sqlite3

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# Add is_optional column to estimates table (default to FALSE for existing estimates)
try:
    cursor.execute('ALTER TABLE estimates ADD COLUMN is_optional BOOLEAN DEFAULT 0')
    print("Added is_optional column to estimates table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column is_optional already exists")
    else:
        raise

conn.commit()
conn.close()
print("Migration complete")

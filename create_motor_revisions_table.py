import sqlite3
from datetime import datetime

conn = sqlite3.connect('estimates.db')
cursor = conn.cursor()

# Create motor_revisions table to track all changes to motors
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motor_revisions (
            revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
            motor_id INTEGER NOT NULL,
            revision_number INTEGER NOT NULL,

            -- Snapshot of all motor fields at time of revision
            load_type VARCHAR(20) NOT NULL,
            motor_name VARCHAR(255) NOT NULL,
            location VARCHAR(100),
            encl_type VARCHAR(50),
            frame VARCHAR(50),
            additional_notes TEXT,
            hp NUMERIC(8, 2),
            speed_range VARCHAR(50),
            voltage NUMERIC(8, 2) NOT NULL,
            qty INTEGER NOT NULL,
            overload_percentage NUMERIC(5, 3),
            continuous_load BOOLEAN NOT NULL,
            vfd_type_id INTEGER,

            -- Load-specific fields
            power_rating NUMERIC(10, 3),
            power_unit VARCHAR(10),
            phase_config VARCHAR(10),

            -- Override options
            nec_amps_override BOOLEAN,
            manual_amps NUMERIC(8, 3),
            vfd_override BOOLEAN,
            selected_vfd_part_id INTEGER,

            -- Metadata
            changed_by VARCHAR(100),
            change_description TEXT,
            created_at DATETIME NOT NULL,

            FOREIGN KEY (motor_id) REFERENCES t_motors(motor_id) ON DELETE CASCADE
        )
    ''')
    print("Created motor_revisions table")

    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_motor_revisions_motor_id
        ON motor_revisions(motor_id, revision_number DESC)
    ''')
    print("Created index on motor_revisions")

    # Add revision_number column to motors table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE t_motors ADD COLUMN revision_number INTEGER DEFAULT 0')
        print("Added revision_number column to t_motors table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column revision_number already exists in t_motors")
        else:
            raise

except sqlite3.OperationalError as e:
    print(f"Note: {e}")

conn.commit()
conn.close()
print("Migration complete")

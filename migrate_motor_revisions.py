"""
Migration script to convert motor revision numbers from Integer to String format (major.minor)
This will convert existing revisions to the new format: 0 -> "0.0", 1 -> "1.0", etc.
"""
# -*- coding: utf-8 -*-
import sys
import io

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import create_app, db
from app.models import Motor, MotorRevision
from sqlalchemy import text

def migrate_motor_revisions():
    """Migrate motor revision numbers to string format"""
    app = create_app()

    with app.app_context():
        print("Starting motor revision migration...")

        try:
            # Clean up any leftover temporary tables from previous failed runs
            print("\n0. Cleaning up any leftover temporary tables...")
            try:
                db.session.execute(text("DROP TABLE IF EXISTS t_motors_new"))
                db.session.execute(text("DROP TABLE IF EXISTS motor_revisions_new"))
                db.session.commit()
                print("   [OK] Cleanup complete")
            except:
                pass

            # First, let's check the current schema
            print("\nChecking current schema...")
            result = db.session.execute(text("PRAGMA table_info(t_motors)"))
            columns = result.fetchall()
            print(f"Current t_motors columns: {[col[1] for col in columns]}")

            result = db.session.execute(text("PRAGMA table_info(motor_revisions)"))
            columns = result.fetchall()
            print(f"Current motor_revisions columns: {[col[1] for col in columns]}")

            # Create temporary tables with new schema
            print("\n1. Creating temporary tables with new schema...")

            # Motors temporary table
            db.session.execute(text("""
                CREATE TABLE t_motors_new (
                    motor_id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    load_type VARCHAR(20) NOT NULL DEFAULT 'motor',
                    motor_name VARCHAR(255) NOT NULL,
                    location VARCHAR(100),
                    encl_type VARCHAR(50),
                    frame VARCHAR(50),
                    additional_notes TEXT,
                    hp NUMERIC(8,2),
                    speed_range VARCHAR(50),
                    voltage NUMERIC(8,2) NOT NULL,
                    qty INTEGER NOT NULL DEFAULT 1,
                    overload_percentage NUMERIC(5,3) DEFAULT 1.15,
                    continuous_load BOOLEAN NOT NULL DEFAULT 1,
                    vfd_type_id INTEGER,
                    power_rating NUMERIC(10,3),
                    power_unit VARCHAR(10) DEFAULT 'kVA',
                    phase_config VARCHAR(10) DEFAULT 'three',
                    nec_amps_override BOOLEAN DEFAULT 0,
                    manual_amps NUMERIC(8,3),
                    vfd_override BOOLEAN DEFAULT 0,
                    selected_vfd_part_id INTEGER,
                    sort_order INTEGER DEFAULT 0,
                    revision_number VARCHAR(20) DEFAULT '0.0',
                    revision_type VARCHAR(20) DEFAULT 'major',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id),
                    FOREIGN KEY (vfd_type_id) REFERENCES t_vfdtype(vfd_type_id),
                    FOREIGN KEY (selected_vfd_part_id) REFERENCES parts(part_id)
                )
            """))

            # Motor revisions temporary table
            db.session.execute(text("""
                CREATE TABLE motor_revisions_new (
                    revision_id INTEGER PRIMARY KEY,
                    motor_id INTEGER NOT NULL,
                    revision_number VARCHAR(20) NOT NULL,
                    revision_type VARCHAR(20) DEFAULT 'major',
                    fields_changed TEXT,
                    load_type VARCHAR(20) NOT NULL,
                    motor_name VARCHAR(255) NOT NULL,
                    location VARCHAR(100),
                    encl_type VARCHAR(50),
                    frame VARCHAR(50),
                    additional_notes TEXT,
                    hp NUMERIC(8,2),
                    speed_range VARCHAR(50),
                    voltage NUMERIC(8,2) NOT NULL,
                    qty INTEGER NOT NULL,
                    overload_percentage NUMERIC(5,3),
                    continuous_load BOOLEAN NOT NULL,
                    vfd_type_id INTEGER,
                    power_rating NUMERIC(10,3),
                    power_unit VARCHAR(10),
                    phase_config VARCHAR(10),
                    nec_amps_override BOOLEAN,
                    manual_amps NUMERIC(8,3),
                    vfd_override BOOLEAN,
                    selected_vfd_part_id INTEGER,
                    changed_by VARCHAR(100),
                    change_description TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (motor_id) REFERENCES t_motors(motor_id)
                )
            """))

            print("   [OK] Temporary tables created")

            # Copy data from old tables to new tables, converting revision numbers
            print("\n2. Copying data and converting revision numbers...")

            # Copy motors data
            db.session.execute(text("""
                INSERT INTO t_motors_new
                SELECT
                    motor_id, project_id, load_type, motor_name, location, encl_type, frame,
                    additional_notes, hp, speed_range, voltage, qty, overload_percentage,
                    continuous_load, vfd_type_id, power_rating, power_unit, phase_config,
                    nec_amps_override, manual_amps, vfd_override, selected_vfd_part_id,
                    sort_order,
                    CAST(revision_number AS TEXT) || '.0' as revision_number,
                    'major' as revision_type,
                    created_at, updated_at
                FROM t_motors
            """))

            motors_count = db.session.execute(text("SELECT COUNT(*) FROM t_motors_new")).scalar()
            print(f"   [OK] Copied {motors_count} motors")

            # Copy motor revisions data
            db.session.execute(text("""
                INSERT INTO motor_revisions_new
                SELECT
                    revision_id, motor_id,
                    CAST(revision_number AS TEXT) || '.0' as revision_number,
                    'major' as revision_type,
                    NULL as fields_changed,
                    load_type, motor_name, location, encl_type, frame, additional_notes,
                    hp, speed_range, voltage, qty, overload_percentage, continuous_load,
                    vfd_type_id, power_rating, power_unit, phase_config,
                    nec_amps_override, manual_amps, vfd_override, selected_vfd_part_id,
                    changed_by, change_description, created_at
                FROM motor_revisions
            """))

            revisions_count = db.session.execute(text("SELECT COUNT(*) FROM motor_revisions_new")).scalar()
            print(f"   [OK] Copied {revisions_count} motor revisions")

            # Drop old tables and rename new tables
            print("\n3. Replacing old tables with new tables...")
            db.session.execute(text("DROP TABLE motor_revisions"))
            db.session.execute(text("DROP TABLE t_motors"))
            db.session.execute(text("ALTER TABLE t_motors_new RENAME TO t_motors"))
            db.session.execute(text("ALTER TABLE motor_revisions_new RENAME TO motor_revisions"))
            print("   [OK] Tables replaced successfully")

            # Commit all changes
            db.session.commit()

            print("\n[SUCCESS] Migration completed successfully!")
            print(f"   - {motors_count} motors migrated")
            print(f"   - {revisions_count} revisions migrated")
            print(f"   - All revision numbers converted to X.0 format")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error during migration: {str(e)}")
            print("Rolling back changes...")

            # Try to clean up temporary tables if they exist
            try:
                db.session.execute(text("DROP TABLE IF EXISTS t_motors_new"))
                db.session.execute(text("DROP TABLE IF EXISTS motor_revisions_new"))
                db.session.commit()
            except:
                pass

            raise

if __name__ == '__main__':
    migrate_motor_revisions()

"""
Database migration to add Engineering Hours estimate functionality
- Adds is_engineering_hours flag to estimates table
- Creates engineering_tasks table for tracking individual engineering tasks
"""

from app import create_app, db
from sqlalchemy import text

def migrate():
    """Run the migration"""
    app = create_app()

    with app.app_context():
        try:
            # Check if is_engineering_hours column exists
            result = db.session.execute(text("PRAGMA table_info(estimates)")).fetchall()
            column_names = [col[1] for col in result]

            if 'is_engineering_hours' not in column_names:
                print("Adding is_engineering_hours column to estimates table...")
                db.session.execute(text(
                    "ALTER TABLE estimates ADD COLUMN is_engineering_hours BOOLEAN DEFAULT 0"
                ))
                db.session.commit()
                print("[OK] Added is_engineering_hours column")
            else:
                print("[OK] is_engineering_hours column already exists")

            # Check if engineering_tasks table exists
            result = db.session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='engineering_tasks'"
            )).fetchone()

            if not result:
                print("Creating engineering_tasks table...")
                db.session.execute(text("""
                    CREATE TABLE engineering_tasks (
                        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        estimate_id INTEGER NOT NULL,
                        task_name VARCHAR(255) NOT NULL,
                        description TEXT,
                        hours NUMERIC(8, 2) NOT NULL DEFAULT 0.0,
                        sort_order INTEGER DEFAULT 0,
                        is_completed BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (estimate_id) REFERENCES estimates(estimate_id) ON DELETE CASCADE
                    )
                """))
                db.session.commit()
                print("[OK] Created engineering_tasks table")
            else:
                print("[OK] engineering_tasks table already exists")

            print("\n[SUCCESS] Migration completed successfully!")
            print("\nNext steps:")
            print("1. Create new projects to auto-generate Engineering Hours estimate")
            print("2. Or manually create an Engineering Hours estimate for existing projects")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Migration failed: {str(e)}")
            raise

if __name__ == '__main__':
    migrate()

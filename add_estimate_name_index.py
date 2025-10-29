"""
Migration script to add index on estimate_name for faster searches
Run this once to improve search performance
"""

from app import create_app, db
from sqlalchemy import text

def add_estimate_name_index():
    """Add index on estimates.estimate_name for faster LIKE searches"""
    app = create_app()

    with app.app_context():
        try:
            # Check if index already exists
            result = db.session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_estimate_name'"
            )).fetchone()

            if result:
                print("Index 'idx_estimate_name' already exists. Skipping.")
                return

            # Create index on estimate_name
            print("Creating index on estimates.estimate_name...")
            db.session.execute(text(
                "CREATE INDEX idx_estimate_name ON estimates(estimate_name)"
            ))
            db.session.commit()
            print("[SUCCESS] Index created successfully!")

            # Verify index was created
            result = db.session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='estimates'"
            )).fetchall()

            print("\nAll indexes on 'estimates' table:")
            for row in result:
                print(f"  - {row[0]}")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error creating index: {e}")
            return

        print("\n[SUCCESS] Migration completed successfully!")

if __name__ == '__main__':
    add_estimate_name_index()

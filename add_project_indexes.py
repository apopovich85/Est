"""
Add indexes to Project table for performance optimization
"""
from app import create_app, db
from sqlalchemy import text

def add_indexes():
    """Add indexes to commonly queried columns"""
    app = create_app()

    with app.app_context():
        try:
            # Check and add index on status column
            print("Adding index on projects.status...")
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)"
            ))

            # Check and add index on updated_at column
            print("Adding index on projects.updated_at...")
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC)"
            ))

            # Check and add index on client_name column for text search
            print("Adding index on projects.client_name...")
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_projects_client_name ON projects(client_name COLLATE NOCASE)"
            ))

            # Add index on estimates.project_id for faster counting (should already exist as FK, but let's ensure)
            print("Adding index on estimates.project_id...")
            db.session.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_estimates_project_id ON estimates(project_id)"
            ))

            db.session.commit()
            print("\nAll indexes added successfully!")

            # Analyze tables for query optimization
            print("\nAnalyzing tables for query optimization...")
            db.session.execute(text("ANALYZE projects"))
            db.session.execute(text("ANALYZE estimates"))
            db.session.commit()
            print("Analysis complete!")

        except Exception as e:
            db.session.rollback()
            print(f"\nError adding indexes: {str(e)}")
            raise

if __name__ == '__main__':
    add_indexes()

#!/usr/bin/env python3
"""
Database migration script to normalize categories
This script will:
1. Create the part_categories table
2. Migrate existing category strings to the new table
3. Update parts to use category_id foreign keys
4. Drop the old category column
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PartCategory, Parts
from datetime import datetime
from sqlalchemy import text

def migrate_categories():
    """Migrate existing category strings to normalized category table"""
    
    app = create_app()
    
    with app.app_context():
        print("Starting category migration...")
        
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created/verified")
        
        # Check if migration is needed
        try:
            # Try to query the old category column
            result = db.session.execute(text("SELECT DISTINCT category FROM parts WHERE category IS NOT NULL AND category != ''"))
            existing_categories = [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"Note: Old category column may not exist: {e}")
            existing_categories = []
        
        if not existing_categories:
            print("No existing categories found to migrate. Migration complete.")
            return
            
        print(f"Found {len(existing_categories)} unique categories to migrate:")
        for cat in sorted(existing_categories):
            print(f"  - {cat}")
        
        # Create category records
        category_mapping = {}
        for cat_name in existing_categories:
            if cat_name and cat_name.strip():
                cat_name = cat_name.strip()
                
                # Check if category already exists
                existing_cat = PartCategory.query.filter_by(name=cat_name).first()
                if existing_cat:
                    category_mapping[cat_name] = existing_cat.category_id
                    print(f"Category '{cat_name}' already exists")
                else:
                    # Create new category
                    new_category = PartCategory(
                        name=cat_name,
                        description=f"Migrated from parts.category field",
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_category)
                    db.session.flush()  # Get the ID
                    category_mapping[cat_name] = new_category.category_id
                    print(f"Created new category: '{cat_name}' (ID: {new_category.category_id})")
        
        # Commit category creations
        db.session.commit()
        print(f"Created/verified {len(category_mapping)} categories")
        
        # Add category_id column to parts table (SQLite specific)
        try:
            # Check if category_id column exists
            try:
                db.session.execute(text("SELECT category_id FROM parts LIMIT 1"))
                print("category_id column already exists")
            except:
                # Add the column
                db.session.execute(text("ALTER TABLE parts ADD COLUMN category_id INTEGER"))
                db.session.commit()
                print("Added category_id column to parts table")
            
            # Update parts to use category_id
            parts_updated = 0
            parts_with_categories = db.session.execute(
                text("SELECT part_id, category FROM parts WHERE category IS NOT NULL AND category != ''")
            ).fetchall()
            
            for part_id, old_category in parts_with_categories:
                if old_category and old_category.strip() in category_mapping:
                    category_id = category_mapping[old_category.strip()]
                    db.session.execute(
                        text("UPDATE parts SET category_id = :cat_id WHERE part_id = :part_id"),
                        {"cat_id": category_id, "part_id": part_id}
                    )
                    parts_updated += 1
            
            db.session.commit()
            print(f"Updated {parts_updated} parts with category_id references")
            
        except Exception as e:
            print(f"Error updating parts: {e}")
            db.session.rollback()
            return False
        
        # Drop the old category column (SQLite doesn't support DROP COLUMN directly)
        # We'll leave it for now and mark it as deprecated in the model
        print("Note: Old 'category' column left in place (SQLite limitation)")
        print("The Parts model now uses category_id with backward compatibility")
        
        # Verify the migration
        total_parts = Parts.query.count()
        categorized_parts = Parts.query.filter(Parts.category_id.isnot(None)).count()
        total_categories = PartCategory.query.count()
        
        print(f"\nMigration Summary:")
        print(f"  Total categories: {total_categories}")
        print(f"  Total parts: {total_parts}")
        print(f"  Parts with categories: {categorized_parts}")
        print(f"  Parts without categories: {total_parts - categorized_parts}")
        
        print("\nCategory migration completed successfully!")
        return True

if __name__ == "__main__":
    try:
        success = migrate_categories()
        if success:
            print("\nMigration completed successfully!")
            sys.exit(0)
        else:
            print("\nMigration failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\nMigration error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
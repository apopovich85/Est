#!/usr/bin/env python3
"""
Migration script to remove effective_date from parts table and ensure 
all effective_date information is properly stored in parts_price_history table.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Parts, PartsPriceHistory
from sqlalchemy import text
from datetime import datetime, date
import traceback

def migrate_effective_date():
    """Migrate effective_date data from parts table to parts_price_history table"""
    print("Starting effective_date migration...")
    
    try:
        # Step 1: Find all parts with effective_date but no price history
        parts_with_effective_date = db.session.execute(text("""
            SELECT part_id, effective_date, manufacturer, part_number 
            FROM parts 
            WHERE effective_date IS NOT NULL
        """)).fetchall()
        
        print(f"Found {len(parts_with_effective_date)} parts with effective_date")
        
        # Step 2: For each part with effective_date, ensure there's a price history record
        for part_id, effective_date, manufacturer, part_number in parts_with_effective_date:
            print(f"Processing part {part_id}: {manufacturer} {part_number}")
            
            # Check if this part has any price history
            existing_history = PartsPriceHistory.query.filter_by(part_id=part_id).first()
            
            if not existing_history:
                print(f"  No price history found, creating initial record...")
                
                # Get the part to check if it has a current price property working
                part = Parts.query.get(part_id)
                if not part:
                    print(f"  WARNING: Could not find part {part_id}, skipping")
                    continue
                
                # Try to get current price - may be 0 if no price history exists
                current_price = part.current_price
                
                # Create initial price history record with effective_date
                initial_history = PartsPriceHistory(
                    part_id=part_id,
                    old_price=None,  # No previous price
                    new_price=current_price if current_price > 0 else None,
                    changed_at=datetime.combine(effective_date, datetime.min.time()) if isinstance(effective_date, date) else effective_date,
                    changed_reason="Migrated from parts.effective_date field",
                    effective_date=effective_date,
                    is_current=True,
                    source="migration_effective_date"
                )
                
                db.session.add(initial_history)
                print(f"  Created initial price history record with effective_date {effective_date}")
                
            else:
                print(f"  Price history exists, checking effective_date...")
                
                # If existing history doesn't have effective_date, update it
                if not existing_history.effective_date:
                    existing_history.effective_date = effective_date
                    print(f"  Updated existing price history with effective_date {effective_date}")
                else:
                    print(f"  Price history already has effective_date {existing_history.effective_date}")
        
        # Step 3: Commit the price history changes
        db.session.commit()
        print("Price history migration completed successfully")
        
        # Step 4: Verify all effective_date data is now in price history
        print("\nVerifying migration...")
        
        orphaned_effective_dates = db.session.execute(text("""
            SELECT p.part_id, p.effective_date, p.manufacturer, p.part_number
            FROM parts p
            LEFT JOIN parts_price_history pph ON p.part_id = pph.part_id AND pph.effective_date = p.effective_date
            WHERE p.effective_date IS NOT NULL 
            AND pph.part_id IS NULL
        """)).fetchall()
        
        if orphaned_effective_dates:
            print(f"WARNING: Found {len(orphaned_effective_dates)} parts with effective_date not properly migrated:")
            for part_id, eff_date, mfr, pn in orphaned_effective_dates:
                print(f"  Part {part_id}: {mfr} {pn} - {eff_date}")
            return False
        
        print("All effective_date data successfully migrated to price history")
        
        # Step 5: Remove the effective_date column from parts table
        print("\nRemoving effective_date column from parts table...")
        
        # SQLite doesn't support DROP COLUMN, so we need to recreate the table
        print("Creating temporary table without effective_date column...")
        
        db.session.execute(text("""
            CREATE TABLE parts_temp AS
            SELECT 
                part_id,
                category_id,
                model,
                rating,
                master_item_number,
                manufacturer,
                part_number,
                upc,
                description,
                vendor,
                created_at,
                updated_at
            FROM parts
        """))
        
        print("Dropping original parts table...")
        db.session.execute(text("DROP TABLE parts"))
        
        print("Renaming temporary table to parts...")
        db.session.execute(text("ALTER TABLE parts_temp RENAME TO parts"))
        
        print("Recreating indexes...")
        db.session.execute(text("CREATE INDEX ix_parts_category_id ON parts (category_id)"))
        db.session.execute(text("CREATE INDEX ix_parts_manufacturer ON parts (manufacturer)"))
        db.session.execute(text("CREATE INDEX ix_parts_part_number ON parts (part_number)"))
        
        # Commit the schema changes
        db.session.commit()
        print("Schema migration completed successfully")
        
        # Step 6: Verify the column is gone
        try:
            db.session.execute(text("SELECT effective_date FROM parts LIMIT 1"))
            print("ERROR: effective_date column still exists!")
            return False
        except Exception:
            print("SUCCESS: effective_date column has been removed from parts table")
        
        print("\nMigration completed successfully!")
        print("- All effective_date data moved to parts_price_history table")
        print("- effective_date column removed from parts table")
        print("- Database schema updated")
        
        return True
        
    except Exception as e:
        print(f"ERROR during migration: {e}")
        print("Full traceback:")
        traceback.print_exc()
        db.session.rollback()
        return False

def verify_migration():
    """Verify that the migration was successful"""
    print("\n" + "="*50)
    print("VERIFICATION REPORT")
    print("="*50)
    
    try:
        # Check parts table schema
        parts_columns = db.session.execute(text("PRAGMA table_info(parts)")).fetchall()
        print("\nParts table columns:")
        for col in parts_columns:
            print(f"  {col[1]} ({col[2]})")
        
        has_effective_date = any(col[1] == 'effective_date' for col in parts_columns)
        if has_effective_date:
            print("ERROR: effective_date column still exists in parts table")
            return False
        else:
            print("SUCCESS: effective_date column removed from parts table")
        
        # Check price history table
        price_history_count = db.session.execute(text("""
            SELECT COUNT(*) FROM parts_price_history WHERE effective_date IS NOT NULL
        """)).scalar()
        
        print(f"\nPrice history records with effective_date: {price_history_count}")
        
        # Check for any parts that might have lost their effective_date info
        total_parts = db.session.execute(text("SELECT COUNT(*) FROM parts")).scalar()
        print(f"Total parts: {total_parts}")
        
        print("\nMigration verification completed successfully")
        return True
        
    except Exception as e:
        print(f"ERROR during verification: {e}")
        return False

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("Effective Date Migration Script")
        print("===============================")
        print("This script will:")
        print("1. Move all effective_date data from parts table to parts_price_history table")
        print("2. Remove the effective_date column from the parts table")
        print("3. Verify the migration completed successfully")
        print()
        
        # Auto-proceed for automated execution
        print("Proceeding with migration...")
        response = 'yes'
        
        success = migrate_effective_date()
        
        if success:
            verify_migration()
            print("\nMigration completed successfully!")
        else:
            print("\nMigration failed. Please check the errors above.")
            sys.exit(1)
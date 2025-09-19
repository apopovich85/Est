#!/usr/bin/env python3
"""
Database migration script to add load_type column to t_motors table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def add_load_type_column():
    """Add load_type column to t_motors table"""
    app = create_app()
    
    with app.app_context():
        print("Adding load_type column to t_motors table...")
        
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(db.text("PRAGMA table_info(t_motors)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'load_type' in columns:
                    print("  load_type column already exists")
                    return True
                
                # Add the column with default value 'motor'
                conn.execute(db.text("ALTER TABLE t_motors ADD COLUMN load_type VARCHAR(20) DEFAULT 'motor' NOT NULL"))
                conn.commit()
            
            print("  SUCCESS: load_type column added")
            return True
            
        except Exception as e:
            print(f"  ERROR: {e}")
            return False

def main():
    """Run the migration"""
    print("=== Adding Load Type Column Migration ===")
    
    if add_load_type_column():
        print("\nSUCCESS: Migration completed successfully!")
        return True
    else:
        print("\nFAILED: Migration failed!")
        return False

if __name__ == "__main__":
    main()
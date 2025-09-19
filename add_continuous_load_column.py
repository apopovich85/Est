#!/usr/bin/env python3
"""
Database migration script to add continuous_load column to t_motors table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

def add_continuous_load_column():
    """Add continuous_load column to t_motors table"""
    app = create_app()
    
    with app.app_context():
        print("Adding continuous_load column to t_motors table...")
        
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(db.text("PRAGMA table_info(t_motors)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'continuous_load' in columns:
                    print("  continuous_load column already exists")
                    return True
                
                # Add the column with default value True
                conn.execute(db.text("ALTER TABLE t_motors ADD COLUMN continuous_load BOOLEAN DEFAULT 1 NOT NULL"))
                conn.commit()
            
            print("  SUCCESS: continuous_load column added")
            return True
            
        except Exception as e:
            print(f"  ERROR: {e}")
            return False

def main():
    """Run the migration"""
    print("=== Adding Continuous Load Column Migration ===")
    
    if add_continuous_load_column():
        print("\nSUCCESS: Migration completed successfully!")
        return True
    else:
        print("\nFAILED: Migration failed!")
        return False

if __name__ == "__main__":
    main()
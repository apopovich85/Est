#!/usr/bin/env python3
"""
Database migration script for Standard Assemblies feature
Creates the new tables required for standard assemblies management
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import StandardAssembly, StandardAssemblyComponent, AssemblyVersion

def migrate_database():
    """Create the new standard assemblies tables"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Starting Standard Assemblies migration...")
        
        try:
            # Create all new tables
            db.create_all()
            print("✅ Successfully created standard assemblies tables:")
            print("   - standard_assemblies")
            print("   - standard_assembly_components") 
            print("   - assembly_versions")
            
            # Add new columns to existing assembly table
            try:
                with db.engine.begin() as conn:
                    # Check if columns already exist
                    result = conn.execute(db.text("PRAGMA table_info(assemblies)"))
                    columns = [row[1] for row in result]
                    
                    if 'standard_assembly_id' not in columns:
                        conn.execute(db.text("ALTER TABLE assemblies ADD COLUMN standard_assembly_id INTEGER"))
                        print("✅ Added standard_assembly_id column to assemblies table")
                    else:
                        print("ℹ️  standard_assembly_id column already exists in assemblies table")
                    
                    if 'standard_assembly_version' not in columns:
                        conn.execute(db.text("ALTER TABLE assemblies ADD COLUMN standard_assembly_version VARCHAR(20)"))
                        print("✅ Added standard_assembly_version column to assemblies table")
                    else:
                        print("ℹ️  standard_assembly_version column already exists in assemblies table")
                    
            except Exception as e:
                print(f"⚠️  Note: Could not modify assemblies table - may already be modified: {e}")
            
            print("\n🎉 Standard Assemblies migration completed successfully!")
            print("\nNext steps:")
            print("1. Start the Flask application")
            print("2. Navigate to 'Standard Assemblies' in the navigation menu") 
            print("3. Create your first standard assembly")
            print("4. Use the drag-and-drop interface to build assemblies")
            print("5. Apply standard assemblies to your estimates")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == "__main__":
    migrate_database()
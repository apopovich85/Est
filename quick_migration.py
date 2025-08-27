#!/usr/bin/env python3
"""
Simple migration script to add standard assemblies columns and tables
"""

import sqlite3
import os

def run_migration():
    # Database path (adjust if needed)
    db_paths = [
        'estimates.db',
        'database/estimates.db',
        os.path.join('database', 'estimates.db')
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Could not find database file. Please check the path.")
        return False
    
    print(f"📊 Found database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🚀 Starting migration...")
        
        # Check if columns already exist in assemblies table
        cursor.execute("PRAGMA table_info(assemblies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add columns if they don't exist
        if 'standard_assembly_id' not in columns:
            cursor.execute("ALTER TABLE assemblies ADD COLUMN standard_assembly_id INTEGER")
            print("✅ Added standard_assembly_id column to assemblies table")
        else:
            print("ℹ️  standard_assembly_id column already exists")
            
        if 'standard_assembly_version' not in columns:
            cursor.execute("ALTER TABLE assemblies ADD COLUMN standard_assembly_version VARCHAR(20)")
            print("✅ Added standard_assembly_version column to assemblies table")
        else:
            print("ℹ️  standard_assembly_version column already exists")
        
        # Create new tables
        tables_sql = [
            """CREATE TABLE IF NOT EXISTS standard_assemblies (
                standard_assembly_id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100) NOT NULL,
                base_assembly_id INTEGER,
                version VARCHAR(20) NOT NULL DEFAULT '1.0',
                is_active BOOLEAN DEFAULT 1,
                is_template BOOLEAN DEFAULT 0,
                created_by VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (base_assembly_id) REFERENCES standard_assemblies (standard_assembly_id)
            )""",
            
            """CREATE TABLE IF NOT EXISTS standard_assembly_components (
                component_id INTEGER PRIMARY KEY,
                standard_assembly_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity DECIMAL(10, 3) NOT NULL DEFAULT 1.000,
                unit_of_measure VARCHAR(20) DEFAULT 'EA',
                notes TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (standard_assembly_id) REFERENCES standard_assemblies (standard_assembly_id),
                FOREIGN KEY (part_id) REFERENCES parts (part_id)
            )""",
            
            """CREATE TABLE IF NOT EXISTS assembly_versions (
                version_id INTEGER PRIMARY KEY,
                standard_assembly_id INTEGER NOT NULL,
                version_number VARCHAR(20) NOT NULL,
                notes TEXT,
                created_by VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (standard_assembly_id) REFERENCES standard_assemblies (standard_assembly_id)
            )"""
        ]
        
        for sql in tables_sql:
            cursor.execute(sql)
        
        print("✅ Created new standard assemblies tables")
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_standard_assemblies_category ON standard_assemblies(category)",
            "CREATE INDEX IF NOT EXISTS idx_standard_assemblies_active ON standard_assemblies(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_standard_assemblies_template ON standard_assemblies(is_template)",
            "CREATE INDEX IF NOT EXISTS idx_standard_assembly_components_assembly ON standard_assembly_components(standard_assembly_id)",
            "CREATE INDEX IF NOT EXISTS idx_standard_assembly_components_part ON standard_assembly_components(part_id)",
            "CREATE INDEX IF NOT EXISTS idx_assembly_versions_assembly ON assembly_versions(standard_assembly_id)"
        ]
        
        for sql in indexes_sql:
            cursor.execute(sql)
        
        print("✅ Created indexes for better performance")
        
        # Commit changes
        conn.commit()
        
        print("\n🎉 Standard Assemblies migration completed successfully!")
        print("\nYou can now:")
        print("1. Start your Flask application")
        print("2. Navigate to 'Standard Assemblies' in the menu")
        print("3. Create and manage standard assemblies")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    if not success:
        exit(1)
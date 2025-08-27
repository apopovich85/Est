import sqlite3
import os

def find_database():
    """Find the SQLite database file"""
    possible_paths = [
        'estimates.db',
        'database/estimates.db',
        os.path.join('database', 'estimates.db')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    print("Database not found in expected locations:")
    for path in possible_paths:
        print(f"  - {path}")
    return None

def migrate():
    db_path = find_database()
    if not db_path:
        return
    
    print(f"Found database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(assemblies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print("Current assemblies table columns:", columns)
        
        # Add missing columns
        if 'standard_assembly_id' not in columns:
            cursor.execute("ALTER TABLE assemblies ADD COLUMN standard_assembly_id INTEGER")
            print("✅ Added standard_assembly_id column")
        
        if 'standard_assembly_version' not in columns:
            cursor.execute("ALTER TABLE assemblies ADD COLUMN standard_assembly_version VARCHAR(20)")
            print("✅ Added standard_assembly_version column")
        
        # Create new tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standard_assemblies (
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
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standard_assembly_components (
                component_id INTEGER PRIMARY KEY,
                standard_assembly_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity DECIMAL(10, 3) NOT NULL DEFAULT 1.000,
                unit_of_measure VARCHAR(20) DEFAULT 'EA',
                notes TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assembly_versions (
                version_id INTEGER PRIMARY KEY,
                standard_assembly_id INTEGER NOT NULL,
                version_number VARCHAR(20) NOT NULL,
                notes TEXT,
                created_by VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ Migration completed!")
        print("\nNext steps:")
        print("1. Stop your Flask app")
        print("2. Uncomment the lines in app/models.py Assembly class:")
        print("   - standard_assembly_id = db.Column(...)")
        print("   - standard_assembly_version = db.Column(...)")
        print("3. Uncomment the standard_assemblies blueprint in app/__init__.py")
        print("4. Uncomment the navigation link in app/templates/base.html")
        print("5. Uncomment the apply button in estimates/detail.html")
        print("6. Restart your Flask app")
        print("7. Navigate to 'Standard Assemblies' to create your first standard assembly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
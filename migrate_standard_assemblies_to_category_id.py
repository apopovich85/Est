#!/usr/bin/env python3

import sqlite3
from app import create_app
from app.models import db, AssemblyCategory, StandardAssembly

def main():
    app = create_app()
    with app.app_context():
        # Use raw SQL to add the new column and migrate data
        conn = sqlite3.connect('estimates.db')
        cursor = conn.cursor()
        
        try:
            # Check if category_id column already exists
            cursor.execute("PRAGMA table_info(standard_assemblies)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'category_id' in columns:
                print("category_id column already exists. Checking if migration is needed...")
                
                # Check if there are any NULL category_id values (indicating incomplete migration)
                cursor.execute("SELECT COUNT(*) FROM standard_assemblies WHERE category_id IS NULL")
                null_count = cursor.fetchone()[0]
                
                if null_count == 0:
                    print("Migration already completed. All assemblies have category_id.")
                    return
                else:
                    print(f"Found {null_count} assemblies with NULL category_id. Continuing migration...")
            else:
                print("Adding category_id column to standard_assemblies table...")
                # Add the new category_id column
                cursor.execute("ALTER TABLE standard_assemblies ADD COLUMN category_id INTEGER")
                
            # Get all assembly categories for mapping
            categories = {}
            cursor.execute("SELECT category_id, code, name FROM assembly_categories")
            for cat_id, code, name in cursor.fetchall():
                categories[code] = cat_id
                categories[name] = cat_id
                # Also map common variations
                if code == 'HS':
                    categories['Hydraulic System'] = cat_id
                elif code == 'WW':
                    categories['Wire Way'] = cat_id
                    categories['Water/Wastewater'] = cat_id
                elif code == 'SG':
                    categories['Squaring Guide'] = cat_id
                    categories['Switch Gear'] = cat_id
                
            print(f"Available categories: {list(categories.keys())}")
            
            # Get all standard assemblies that need migration
            cursor.execute("SELECT standard_assembly_id, name, category FROM standard_assemblies WHERE category_id IS NULL")
            assemblies_to_migrate = cursor.fetchall()
            
            print(f"Found {len(assemblies_to_migrate)} assemblies to migrate...")
            
            migrated_count = 0
            unmapped_categories = set()
            
            for assembly_id, name, old_category in assemblies_to_migrate:
                category_id = None
                
                # Try to map the old category to a new category_id
                if old_category in categories:
                    category_id = categories[old_category]
                elif old_category == 'VFD':
                    category_id = categories.get('VFD', None)
                elif old_category == 'Electrical':
                    # Map 'Electrical' to VFD as a reasonable default
                    category_id = categories.get('VFD', None)
                elif old_category == 'Hydraulic':
                    category_id = categories.get('HS', None)
                elif old_category == 'WireWay':
                    category_id = categories.get('WW', None)
                else:
                    # Try partial matching
                    for cat_name, cat_id in categories.items():
                        if old_category.lower() in cat_name.lower() or cat_name.lower() in old_category.lower():
                            category_id = cat_id
                            break
                
                if category_id:
                    cursor.execute("UPDATE standard_assemblies SET category_id = ? WHERE standard_assembly_id = ?", 
                                 (category_id, assembly_id))
                    migrated_count += 1
                    print(f"  Migrated {name}: '{old_category}' -> category_id {category_id}")
                else:
                    unmapped_categories.add(old_category)
                    # Default to VFD if we can't map
                    default_category_id = categories.get('VFD', 1)
                    cursor.execute("UPDATE standard_assemblies SET category_id = ? WHERE standard_assembly_id = ?", 
                                 (default_category_id, assembly_id))
                    migrated_count += 1
                    print(f"  Migrated {name}: '{old_category}' -> VFD (default)")
            
            if unmapped_categories:
                print(f"\\nWarning: Could not directly map these categories: {unmapped_categories}")
                print("They were mapped to VFD as default. You may want to update them manually.")
            
            # Now try to drop the old category column (this might fail if there are constraints)
            try:
                # Create a new table without the category column
                cursor.execute('''
                CREATE TABLE standard_assemblies_new (
                    standard_assembly_id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    category_id INTEGER NOT NULL,
                    base_assembly_id INTEGER,
                    version VARCHAR(20) NOT NULL DEFAULT '1.0',
                    is_active BOOLEAN DEFAULT 1,
                    is_template BOOLEAN DEFAULT 0,
                    created_by VARCHAR(100),
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY (category_id) REFERENCES assembly_categories(category_id),
                    FOREIGN KEY (base_assembly_id) REFERENCES standard_assemblies(standard_assembly_id)
                )
                ''')
                
                # Copy data to new table
                cursor.execute('''
                INSERT INTO standard_assemblies_new 
                SELECT standard_assembly_id, name, description, category_id, base_assembly_id, 
                       version, is_active, is_template, created_by, created_at, updated_at
                FROM standard_assemblies
                ''')
                
                # Drop old table and rename new one
                cursor.execute('DROP TABLE standard_assemblies')
                cursor.execute('ALTER TABLE standard_assemblies_new RENAME TO standard_assemblies')
                
                print("Successfully removed old category column")
                
            except Exception as e:
                print(f"Could not remove old category column: {e}")
                print("The migration was successful, but you may want to manually clean up the old column")
            
            conn.commit()
            print(f"\\nMigration completed! Migrated {migrated_count} assemblies to use category_id.")
            
        except Exception as e:
            conn.rollback()
            print(f"Migration failed: {e}")
            raise
        finally:
            conn.close()

if __name__ == '__main__':
    main()
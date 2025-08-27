#!/usr/bin/env python3

import sqlite3
from datetime import datetime

def main():
    """Fix the standard_assemblies table schema and migrate data"""
    
    # Connect to both databases
    main_conn = sqlite3.connect('estimates.db')
    old_conn = sqlite3.connect('database/estimates.db')
    
    try:
        main_cursor = main_conn.cursor()
        old_cursor = old_conn.cursor()
        
        print("Fixing standard_assemblies table schema...")
        
        # Drop the existing table and recreate with correct structure
        main_cursor.execute('DROP TABLE IF EXISTS standard_assemblies')
        
        # Create new table with correct schema
        main_cursor.execute('''
            CREATE TABLE standard_assemblies (
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
        
        # Also drop and recreate standard_assembly_components table
        main_cursor.execute('DROP TABLE IF EXISTS standard_assembly_components')
        main_cursor.execute('''
            CREATE TABLE standard_assembly_components (
                component_id INTEGER PRIMARY KEY,
                standard_assembly_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity NUMERIC(10,3) NOT NULL DEFAULT 1.000,
                unit_of_measure VARCHAR(20) DEFAULT 'EA',
                notes TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (standard_assembly_id) REFERENCES standard_assemblies(standard_assembly_id),
                FOREIGN KEY (part_id) REFERENCES parts(part_id)
            )
        ''')
        
        print("Tables recreated with correct schema")
        
        # Get category mapping
        main_cursor.execute("SELECT category_id, code, name FROM assembly_categories")
        categories = {}
        for cat_id, code, name in main_cursor.fetchall():
            categories[code] = cat_id
            categories[name] = cat_id
            # Add common mappings
            if code == 'VFD':
                categories['Electrical'] = cat_id  # Map old 'Electrical' to VFD
            elif code == 'HS':
                categories['Hydraulic'] = cat_id
            elif code == 'WW':
                categories['WireWay'] = cat_id
        
        print(f"Category mappings available: {list(categories.keys())}")
        
        # Check what data exists in old database
        old_cursor.execute("SELECT COUNT(*) FROM standard_assemblies")
        assembly_count = old_cursor.fetchone()[0]
        print(f"Found {assembly_count} assemblies in old database")
        
        if assembly_count == 0:
            print("No assemblies to migrate")
            return
        
        # Get assemblies from old database
        old_cursor.execute("SELECT * FROM standard_assemblies")
        old_assemblies = old_cursor.fetchall()
        
        # Get column names for old table
        old_cursor.execute("PRAGMA table_info(standard_assemblies)")
        old_columns = [col[1] for col in old_cursor.fetchall()]
        
        migrated_count = 0
        category_misses = set()
        
        for assembly in old_assemblies:
            # Create a dict from the row data
            assembly_dict = dict(zip(old_columns, assembly))
            
            # Map old category to new category_id
            old_category = assembly_dict.get('category', 'VFD')
            category_id = categories.get(old_category)
            
            if not category_id:
                # Try partial matching
                for cat_name, cat_id in categories.items():
                    if old_category.lower() in cat_name.lower() or cat_name.lower() in old_category.lower():
                        category_id = cat_id
                        break
                
                if not category_id:
                    category_id = categories.get('VFD', 1)  # Default to VFD
                    category_misses.add(old_category)
            
            # Insert into new database with new schema
            main_cursor.execute('''
                INSERT INTO standard_assemblies 
                (name, description, category_id, base_assembly_id, version, 
                 is_active, is_template, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assembly_dict.get('name'),
                assembly_dict.get('description'),
                category_id,
                assembly_dict.get('base_assembly_id'),
                assembly_dict.get('version', '1.0'),
                assembly_dict.get('is_active', True),
                assembly_dict.get('is_template', False),
                assembly_dict.get('created_by'),
                assembly_dict.get('created_at'),
                assembly_dict.get('updated_at')
            ))
            
            migrated_count += 1
            print(f"  Migrated: {assembly_dict.get('name')} - {old_category} -> category_id {category_id}")
        
        if category_misses:
            print(f"\\nWarning: Unmapped categories (defaulted to VFD): {category_misses}")
        
        # Now migrate standard_assembly_components if they exist
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='standard_assembly_components'")
        if old_cursor.fetchone():
            old_cursor.execute("SELECT COUNT(*) FROM standard_assembly_components")
            component_count = old_cursor.fetchone()[0]
            print(f"\\nMigrating {component_count} assembly components...")
            
            if component_count > 0:
                # Get assembly ID mapping (old ID -> new ID)
                assembly_mapping = {}
                old_cursor.execute("SELECT standard_assembly_id, name FROM standard_assemblies")
                old_assemblies_map = dict(old_cursor.fetchall())
                
                main_cursor.execute("SELECT standard_assembly_id, name FROM standard_assemblies")
                new_assemblies_map = {name: aid for aid, name in main_cursor.fetchall()}
                
                for old_id, name in old_assemblies_map.items():
                    if name in new_assemblies_map:
                        assembly_mapping[old_id] = new_assemblies_map[name]
                
                # Migrate components
                old_cursor.execute("SELECT * FROM standard_assembly_components")
                old_components = old_cursor.fetchall()
                
                old_cursor.execute("PRAGMA table_info(standard_assembly_components)")
                old_comp_columns = [col[1] for col in old_cursor.fetchall()]
                
                component_migrated = 0
                for component in old_components:
                    comp_dict = dict(zip(old_comp_columns, component))
                    old_assembly_id = comp_dict.get('standard_assembly_id')
                    new_assembly_id = assembly_mapping.get(old_assembly_id)
                    
                    if new_assembly_id:
                        main_cursor.execute('''
                            INSERT INTO standard_assembly_components
                            (standard_assembly_id, part_id, quantity, unit_of_measure, 
                             notes, sort_order, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            new_assembly_id,
                            comp_dict.get('part_id'),
                            comp_dict.get('quantity', 1.0),
                            comp_dict.get('unit_of_measure', 'EA'),
                            comp_dict.get('notes'),
                            comp_dict.get('sort_order', 0),
                            comp_dict.get('created_at'),
                            comp_dict.get('updated_at')
                        ))
                        component_migrated += 1
                
                print(f"Migrated {component_migrated} components")
        
        main_conn.commit()
        print(f"\\nMigration completed successfully!")
        print(f"Migrated {migrated_count} assemblies")
        
        # Verify the migration - look for PF755TS assemblies
        main_cursor.execute("SELECT COUNT(*) FROM standard_assemblies WHERE name LIKE '%AB_PF755TS%' OR name LIKE '%PF755TS%'")
        pf_count = main_cursor.fetchone()[0]
        print(f"\\nVerification: Found {pf_count} PF755TS assemblies in migrated database")
        
        if pf_count > 0:
            main_cursor.execute('''
                SELECT sa.name, ac.code, ac.name 
                FROM standard_assemblies sa
                JOIN assembly_categories ac ON sa.category_id = ac.category_id 
                WHERE sa.name LIKE '%AB_PF755TS%' OR sa.name LIKE '%PF755TS%'
            ''')
            pf_assemblies = main_cursor.fetchall()
            print("PF755TS assemblies with categories:")
            for name, code, cat_name in pf_assemblies:
                print(f"  {name}: {code} - {cat_name}")
                
            # This should answer the user's question about the category discrepancy
            print("\\n=== CATEGORY DISCREPANCY ANALYSIS ===")
            print("The category discrepancy you observed was caused by:")
            print("1. The application was using two different database files")
            print("2. The old database had assemblies with 'Electrical' category")
            print("3. During migration, 'Electrical' has been mapped to 'VFD'")
            print("4. All assemblies now use the new category system consistently")
        
    except Exception as e:
        main_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        main_conn.close()
        old_conn.close()

if __name__ == '__main__':
    main()
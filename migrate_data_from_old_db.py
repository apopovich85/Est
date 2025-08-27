#!/usr/bin/env python3

import sqlite3
from app import create_app
from app.models import db, AssemblyCategory

def main():
    """Migrate data from database/estimates.db to main estimates.db with proper schema"""
    
    # First ensure the main database has the correct schema
    app = create_app()
    with app.app_context():
        # Create all tables with new schema
        db.create_all()
        
        # Populate assembly categories if they don't exist
        existing_count = AssemblyCategory.query.count()
        if existing_count == 0:
            print("Creating assembly categories...")
            initial_categories = [
                {'code': 'VFD', 'name': 'Variable Frequency Drive', 'description': 'Variable frequency drives for motor control', 'sort_order': 10},
                {'code': 'FVNR', 'name': 'Full Voltage Non-Reversing', 'description': 'Full voltage non-reversing motor starters', 'sort_order': 20},
                {'code': 'CAB', 'name': 'Cabinet', 'description': 'Control cabinets and enclosures', 'sort_order': 30},
                {'code': 'COOLING', 'name': 'Cooling', 'description': 'Cooling systems and ventilation', 'sort_order': 40},
                {'code': 'MCCB', 'name': 'Molded Case Circuit Breaker', 'description': 'Molded case circuit breakers', 'sort_order': 50},
                {'code': 'PDB', 'name': 'Power Distribution Block', 'description': 'Power distribution blocks and panels', 'sort_order': 60},
                {'code': 'XFMR-CTRL', 'name': 'Transformer Control', 'description': 'Transformer control systems', 'sort_order': 70},
                {'code': 'PDB-FU', 'name': 'Fused Power Distribution Block', 'description': 'Fused power distribution blocks', 'sort_order': 80},
                {'code': 'RIO', 'name': 'Remote I/O', 'description': 'Remote input/output modules', 'sort_order': 90},
                {'code': 'OS', 'name': 'Operator Station', 'description': 'Operator stations and HMI panels', 'sort_order': 100},
                {'code': 'INST-LAS', 'name': 'Laser Instrumentation', 'description': 'Laser measurement and instrumentation', 'sort_order': 110},
                {'code': 'PLC', 'name': 'Programmable Logic Controller', 'description': 'PLCs and control processors', 'sort_order': 120},
                {'code': 'WW', 'name': 'Wire Way', 'description': 'Wire ways and cable management', 'sort_order': 130},
                {'code': 'INST-PRS', 'name': 'Pressure Instrumentation', 'description': 'Pressure measurement instrumentation', 'sort_order': 140},
                {'code': 'LVM', 'name': 'Low Voltage Motor', 'description': 'Low voltage motor controls', 'sort_order': 150},
                {'code': 'SG', 'name': 'Squaring Guide', 'description': 'Squaring guides and positioning systems', 'sort_order': 160},
                {'code': 'LVST', 'name': 'Low Voltage Starter', 'description': 'Low voltage motor starters', 'sort_order': 170},
                {'code': 'HS', 'name': 'Hydraulic System', 'description': 'Hydraulic systems and controls', 'sort_order': 180},
            ]
            
            for cat_data in initial_categories:
                category = AssemblyCategory(
                    code=cat_data['code'],
                    name=cat_data['name'],
                    description=cat_data['description'],
                    sort_order=cat_data['sort_order'],
                    is_active=True
                )
                db.session.add(category)
            
            db.session.commit()
            print(f"Created {len(initial_categories)} assembly categories")
    
    # Now migrate data using raw SQL
    main_conn = sqlite3.connect('estimates.db')
    old_conn = sqlite3.connect('database/estimates.db')
    
    try:
        main_cursor = main_conn.cursor()
        old_cursor = old_conn.cursor()
        
        print("\\nMigrating data from database/estimates.db to estimates.db...")
        
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
        
        print(f"Category mappings: {categories}")
        
        # Check what data exists in old database
        old_cursor.execute("SELECT COUNT(*) FROM standard_assemblies")
        assembly_count = old_cursor.fetchone()[0]
        print(f"Found {assembly_count} assemblies in old database")
        
        # Get assemblies from old database
        old_cursor.execute("SELECT * FROM standard_assemblies")
        old_assemblies = old_cursor.fetchall()
        
        # Get column names for old table
        old_cursor.execute("PRAGMA table_info(standard_assemblies)")
        old_columns = [col[1] for col in old_cursor.fetchall()]
        print(f"Old table columns: {old_columns}")
        
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
        
        # Now migrate standard_assembly_components
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='standard_assembly_components'")
        if old_cursor.fetchone():
            old_cursor.execute("SELECT COUNT(*) FROM standard_assembly_components")
            component_count = old_cursor.fetchone()[0]
            print(f"\\nMigrating {component_count} assembly components...")
            
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
        
        # Verify the migration
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
        
    except Exception as e:
        main_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        main_conn.close()
        old_conn.close()

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
One-time CSV import script for standard assemblies
Processes ImportData/assemblies (2).csv and imports VFD equipment only
"""

import csv
import sqlite3
from datetime import datetime
import os

def get_or_create_category(cursor, category_code):
    """Get category ID by code, create if doesn't exist"""
    cursor.execute('SELECT category_id FROM assembly_categories WHERE code = ?', (category_code,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        # Create category if it doesn't exist
        category_names = {
            'CAB': 'Cabinet',
            'VFD': 'Variable Frequency Drive',
            'FVNR': 'Full Voltage Non-Reversing',
            'COOLING': 'Cooling',
            'MCCB': 'Molded Case Circuit Breaker',
            'PDB': 'Power Distribution Block',
            'PLC': 'Programmable Logic Controller'
        }
        
        name = category_names.get(category_code, category_code.title())
        cursor.execute('''
            INSERT INTO assembly_categories (code, name, description, sort_order, is_active)
            VALUES (?, ?, ?, 99, 1)
        ''', (category_code, name, f"{name} assemblies"))
        return cursor.lastrowid

def get_part_id(cursor, part_number):
    """Look up part_id by part_number"""
    cursor.execute('SELECT part_id FROM parts WHERE part_number = ?', (part_number,))
    result = cursor.fetchone()
    return result[0] if result else None

def import_assemblies():
    """Main import function"""
    csv_file = r'C:\Projects\Est_v0.5\ImportData\assemblies (2).csv'
    
    if not os.path.exists(csv_file):
        print(f"ERROR: CSV file not found at {csv_file}")
        return
    
    conn = sqlite3.connect('estimates.db')
    cursor = conn.cursor()
    
    try:
        # Read and process CSV
        assemblies_data = {}
        unmapped_parts = []
        category_ids = {}  # Cache category IDs
        
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                assembly_cat = row['AssemblyCat'].strip()
                
                # Process all assembly categories (not just VFD)
                # Get or cache the category ID
                if assembly_cat not in category_ids:
                    category_ids[assembly_cat] = get_or_create_category(cursor, assembly_cat)
                    print(f"Category {assembly_cat} ID: {category_ids[assembly_cat]}")
                
                assembly_id = row['Assembly_ID'].strip()
                component_part_number = row['Component_Part_Number'].strip()
                quantity = float(row['Quantity']) if row['Quantity'].strip() else 1.0
                assy_num = row['Assy_%23'].strip()
                
                # Group by Assy_# (each unique Assy_# is one assembly)
                if assy_num not in assemblies_data:
                    assemblies_data[assy_num] = {
                        'assembly_name': assembly_id,
                        'category': assembly_cat,
                        'category_id': category_ids[assembly_cat],
                        'components': []
                    }
                
                # Look up part_id for this component
                part_id = get_part_id(cursor, component_part_number)
                
                if part_id:
                    assemblies_data[assy_num]['components'].append({
                        'part_id': part_id,
                        'part_number': component_part_number,
                        'quantity': quantity
                    })
                else:
                    unmapped_parts.append(component_part_number)
        
        print(f"\\nFound {len(assemblies_data)} assemblies to import")
        print(f"Found {len(set(unmapped_parts))} unique unmapped parts")
        
        # Group by category for reporting
        by_category = {}
        for assy_data in assemblies_data.values():
            cat = assy_data['category']
            by_category[cat] = by_category.get(cat, 0) + 1
        
        print("\\nAssemblies by category:")
        for cat, count in by_category.items():
            print(f"  - {cat}: {count}")
        
        # Import assemblies with duplicate checking
        imported_count = 0
        skipped_count = 0
        for assy_num, assy_data in assemblies_data.items():
            if not assy_data['components']:  # Skip assemblies with no valid components
                print(f"Skipping {assy_data['assembly_name']} - no valid components found")
                continue
            
            # Check if assembly already exists by assembly_number (Assy_#)
            cursor.execute('SELECT standard_assembly_id FROM standard_assemblies WHERE assembly_number = ?', (assy_num,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"SKIP {assy_data['assembly_name']} ({assy_num}) - already exists")
                skipped_count += 1
                continue
            
            # Insert standard assembly with assembly_number and correct category
            cursor.execute('''
                INSERT INTO standard_assemblies 
                (name, assembly_number, description, category_id, version, is_active, is_template, created_at)
                VALUES (?, ?, ?, ?, "1.0", 1, 1, ?)
            ''', (assy_data['assembly_name'], assy_num, '', assy_data['category_id'], datetime.now()))
            
            standard_assembly_id = cursor.lastrowid
            
            # Insert components for this assembly
            sort_order = 1
            for component in assy_data['components']:
                cursor.execute('''
                    INSERT INTO standard_assembly_components
                    (standard_assembly_id, part_id, quantity, sort_order, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (standard_assembly_id, component['part_id'], component['quantity'], 
                      sort_order, datetime.now()))
                sort_order += 1
            
            imported_count += 1
            print(f"OK Imported: {assy_data['assembly_name']} ({len(assy_data['components'])} components)")
        
        # Report results
        print(f"\\n=== IMPORT SUMMARY ===")
        print(f"Assemblies imported: {imported_count}")
        print(f"Assemblies skipped (duplicates): {skipped_count}")
        print(f"Total assemblies found: {len(assemblies_data)}")
        
        # Report by category
        imported_by_category = {}
        cursor.execute('''
            SELECT ac.code, COUNT(*) 
            FROM standard_assemblies sa
            JOIN assembly_categories ac ON sa.category_id = ac.category_id
            WHERE sa.assembly_number IS NOT NULL
            GROUP BY ac.code
        ''')
        for code, count in cursor.fetchall():
            imported_by_category[code] = count
            
        print("\\nImported assemblies by category:")
        for code, count in imported_by_category.items():
            print(f"  - {code}: {count}")
        
        # Report unmapped parts
        unique_unmapped = sorted(set(unmapped_parts))
        print(f"\\n=== UNMAPPED COMPONENT PARTS ({len(unique_unmapped)}) ===")
        for part_num in unique_unmapped:
            print(f"  {part_num}")
        
        conn.commit()
        print(f"\\nOK Import completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import_assemblies()
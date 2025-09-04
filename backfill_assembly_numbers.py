#!/usr/bin/env python3
"""
Backfill assembly_number field for existing VFD assemblies
"""

import csv
import sqlite3
import os

def backfill_assembly_numbers():
    """Backfill assembly numbers from original CSV"""
    csv_file = r'C:\Projects\Est_v0.5\ImportData\assemblies (2).csv'
    
    if not os.path.exists(csv_file):
        print(f"ERROR: CSV file not found at {csv_file}")
        return
    
    conn = sqlite3.connect('estimates.db')
    cursor = conn.cursor()
    
    try:
        # Read CSV and build mapping of assembly names to Assy_#
        name_to_assy_num = {}
        
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                assembly_cat = row['AssemblyCat'].strip()
                if assembly_cat == 'VFD':
                    assembly_name = row['Assembly_ID'].strip()
                    assy_num = row['Assy_%23'].strip()
                    name_to_assy_num[assembly_name] = assy_num
        
        print(f"Found {len(name_to_assy_num)} unique VFD assemblies in CSV")
        
        # Update existing assemblies with their assembly numbers
        updated_count = 0
        for assembly_name, assy_num in name_to_assy_num.items():
            cursor.execute('''
                UPDATE standard_assemblies 
                SET assembly_number = ?
                WHERE name = ? AND assembly_number IS NULL
            ''', (assy_num, assembly_name))
            
            if cursor.rowcount > 0:
                print(f"Updated {assembly_name} -> {assy_num}")
                updated_count += 1
        
        conn.commit()
        print(f"\\nOK Updated {updated_count} assemblies with assembly numbers")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    backfill_assembly_numbers()
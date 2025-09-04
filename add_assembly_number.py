#!/usr/bin/env python3
"""
Migration script to add assembly_number column to standard_assemblies table
"""

import sqlite3
from datetime import datetime

def add_assembly_number():
    """Add assembly_number column to standard_assemblies table"""
    conn = sqlite3.connect('estimates.db')
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(standard_assemblies)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'assembly_number' in column_names:
            print("OK Assembly_number column already exists in standard_assemblies table")
            return
        
        print("Adding assembly_number column to standard_assemblies table...")
        cursor.execute('ALTER TABLE standard_assemblies ADD COLUMN assembly_number VARCHAR(50)')
        
        # Create index for performance
        cursor.execute('CREATE INDEX idx_standard_assemblies_assembly_number ON standard_assemblies(assembly_number)')
        
        conn.commit()
        print("OK Successfully added assembly_number column to standard_assemblies table")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_assembly_number()
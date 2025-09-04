#!/usr/bin/env python3
"""
Migration script to add quantity column to assemblies table
"""

import sqlite3
from datetime import datetime

def add_assembly_quantity():
    """Add quantity column to assemblies table"""
    conn = sqlite3.connect('estimates.db')
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(assemblies)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'quantity' in column_names:
            print("OK Quantity column already exists in assemblies table")
            return
        
        print("Adding quantity column to assemblies table...")
        cursor.execute('ALTER TABLE assemblies ADD COLUMN quantity NUMERIC(10, 3) DEFAULT 1.0')
        
        # Update existing assemblies to have quantity = 1.0
        cursor.execute('UPDATE assemblies SET quantity = 1.0 WHERE quantity IS NULL')
        
        conn.commit()
        print("OK Successfully added quantity column to assemblies table")
        
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_assembly_quantity()
#!/usr/bin/env python3

import sqlite3
from datetime import datetime

def main():
    """Complete data migration from database/estimates.db to main estimates.db"""
    
    # Connect to both databases
    main_conn = sqlite3.connect('estimates.db')
    old_conn = sqlite3.connect('database/estimates.db')
    
    try:
        main_cursor = main_conn.cursor()
        old_cursor = old_conn.cursor()
        
        print("=== COMPLETE DATA MIGRATION ===")
        print("Moving ALL data from database/estimates.db to main estimates.db")
        
        # First, create missing tables in main database
        print("\n1. Creating missing tables...")
        
        # Create parts table if it doesn't exist
        main_cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                part_id INTEGER PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                model VARCHAR(100),
                rating VARCHAR(50),
                master_item_number VARCHAR(100),
                manufacturer VARCHAR(100) NOT NULL,
                part_number VARCHAR(100) NOT NULL,
                upc VARCHAR(50),
                description TEXT,
                price NUMERIC(12,2),
                vendor VARCHAR(100),
                effective_date DATE,
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')
        
        # Create parts_price_history table if it doesn't exist
        main_cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_price_history (
                history_id INTEGER PRIMARY KEY,
                part_id INTEGER NOT NULL,
                old_price NUMERIC(12,2),
                new_price NUMERIC(12,2),
                changed_at DATETIME,
                changed_reason VARCHAR(255),
                FOREIGN KEY (part_id) REFERENCES parts(part_id)
            )
        ''')
        
        # Create assembly_parts table if it doesn't exist
        main_cursor.execute('''
            CREATE TABLE IF NOT EXISTS assembly_parts (
                component_id INTEGER PRIMARY KEY,
                assembly_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity NUMERIC(10,3) NOT NULL DEFAULT 1.000,
                unit_of_measure VARCHAR(20) DEFAULT 'EA',
                notes TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (assembly_id) REFERENCES assemblies(assembly_id),
                FOREIGN KEY (part_id) REFERENCES parts(part_id)
            )
        ''')
        
        print("Tables created successfully")
        
        # 2. Migrate PARTS data (this is the big one!)
        print("\\n2. Migrating parts data...")
        old_cursor.execute("SELECT COUNT(*) FROM parts")
        parts_count = old_cursor.fetchone()[0]
        print(f"Found {parts_count} parts to migrate")
        
        if parts_count > 0:
            # Clear existing parts data first
            main_cursor.execute("DELETE FROM parts")
            
            # Get parts data
            old_cursor.execute("SELECT * FROM parts")
            parts_data = old_cursor.fetchall()
            
            # Get column names
            old_cursor.execute("PRAGMA table_info(parts)")
            parts_columns = [col[1] for col in old_cursor.fetchall()]
            
            migrated_parts = 0
            for part in parts_data:
                part_dict = dict(zip(parts_columns, part))
                
                # Insert part
                main_cursor.execute('''
                    INSERT INTO parts 
                    (category, model, rating, master_item_number, manufacturer, 
                     part_number, upc, description, price, vendor, effective_date, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    part_dict.get('category'),
                    part_dict.get('model'),
                    part_dict.get('rating'),
                    part_dict.get('master_item_number'),
                    part_dict.get('manufacturer'),
                    part_dict.get('part_number'),
                    part_dict.get('upc'),
                    part_dict.get('description'),
                    part_dict.get('price'),
                    part_dict.get('vendor'),
                    part_dict.get('effective_date'),
                    part_dict.get('created_at'),
                    part_dict.get('updated_at')
                ))
                migrated_parts += 1
                
                if migrated_parts % 50 == 0:
                    print(f"  Migrated {migrated_parts} parts...")
            
            print(f"Successfully migrated {migrated_parts} parts")
        
        # 3. Migrate parts_price_history if it exists and has data
        print("\\n3. Migrating parts price history...")
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parts_price_history'")
        if old_cursor.fetchone():
            old_cursor.execute("SELECT COUNT(*) FROM parts_price_history")
            history_count = old_cursor.fetchone()[0]
            print(f"Found {history_count} price history records")
            
            if history_count > 0:
                # Migrate price history
                old_cursor.execute("SELECT * FROM parts_price_history")
                history_data = old_cursor.fetchall()
                
                old_cursor.execute("PRAGMA table_info(parts_price_history)")
                history_columns = [col[1] for col in old_cursor.fetchall()]
                
                for history in history_data:
                    history_dict = dict(zip(history_columns, history))
                    main_cursor.execute('''
                        INSERT INTO parts_price_history
                        (part_id, old_price, new_price, changed_at, changed_reason)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        history_dict.get('part_id'),
                        history_dict.get('old_price'),
                        history_dict.get('new_price'),
                        history_dict.get('changed_at'),
                        history_dict.get('changed_reason')
                    ))
                
                print(f"Migrated {history_count} price history records")
        else:
            print("No parts_price_history table found")
        
        # 4. Migrate assembly_parts if it exists and has data
        print("\\n4. Migrating assembly_parts...")
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assembly_parts'")
        if old_cursor.fetchone():
            old_cursor.execute("SELECT COUNT(*) FROM assembly_parts")
            assembly_parts_count = old_cursor.fetchone()[0]
            print(f"Found {assembly_parts_count} assembly_parts records")
            
            if assembly_parts_count > 0:
                old_cursor.execute("SELECT * FROM assembly_parts")
                assembly_parts_data = old_cursor.fetchall()
                
                old_cursor.execute("PRAGMA table_info(assembly_parts)")
                assembly_parts_columns = [col[1] for col in old_cursor.fetchall()]
                
                for ap in assembly_parts_data:
                    ap_dict = dict(zip(assembly_parts_columns, ap))
                    main_cursor.execute('''
                        INSERT INTO assembly_parts
                        (assembly_id, part_id, quantity, unit_of_measure, 
                         notes, sort_order, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ap_dict.get('assembly_id'),
                        ap_dict.get('part_id'),
                        ap_dict.get('quantity', 1.0),
                        ap_dict.get('unit_of_measure', 'EA'),
                        ap_dict.get('notes'),
                        ap_dict.get('sort_order', 0),
                        ap_dict.get('created_at'),
                        ap_dict.get('updated_at')
                    ))
                
                print(f"Migrated {assembly_parts_count} assembly_parts records")
        else:
            print("No assembly_parts table found")
        
        # 5. Check for any other tables with data that we might have missed
        print("\\n5. Checking for other data to migrate...")
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        old_tables = [t[0] for t in old_cursor.fetchall()]
        
        main_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        main_tables = [t[0] for t in main_cursor.fetchall()]
        
        for table in old_tables:
            if table not in ['parts', 'parts_price_history', 'assembly_parts', 'standard_assemblies', 
                           'standard_assembly_components', 'assembly_categories', 'sqlite_sequence']:
                old_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = old_cursor.fetchone()[0]
                if count > 0:
                    print(f"  {table}: {count} records (review needed)")
        
        main_conn.commit()
        print("\\n=== MIGRATION COMPLETED ===")
        
        # 6. Verification
        print("\\n6. Verification - Final record counts:")
        main_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in main_cursor.fetchall()]
        
        for table in sorted(tables):
            main_cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = main_cursor.fetchone()[0]
            print(f'  {table}: {count} records')
        
        # Special verification for parts
        if 'parts' in tables:
            main_cursor.execute("SELECT COUNT(*) FROM parts WHERE part_number LIKE '%PF755%' OR description LIKE '%PF755%'")
            pf_parts = main_cursor.fetchone()[0]
            print(f"\\nPF755-related parts: {pf_parts}")
            
            if pf_parts > 0:
                main_cursor.execute("SELECT part_number, description, price FROM parts WHERE part_number LIKE '%PF755%' OR description LIKE '%PF755%' LIMIT 3")
                sample_parts = main_cursor.fetchall()
                print("Sample PF755 parts:")
                for part in sample_parts:
                    print(f"  {part[0]}: {part[1]} - ${part[2]}")
        
    except Exception as e:
        main_conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        main_conn.close()
        old_conn.close()

if __name__ == '__main__':
    main()
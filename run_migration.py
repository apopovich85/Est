#!/usr/bin/env python3
"""
Migration script to convert Components to Parts-based system
Run this after updating the models but before dropping the old tables.
"""

import os
import sys
from datetime import datetime
import sqlite3

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Component, Parts, AssemblyPart, PartsPriceHistory, PriceHistory

def backup_database():
    """Create a backup of the database before migration"""
    db_path = "estimates.db"
    backup_path = f"estimates_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    else:
        print("⚠️  Database file not found - creating new database")
        return None

def create_tables():
    """Create new tables"""
    print("📝 Creating new tables...")
    db.create_all()
    print("✅ Tables created successfully")

def migrate_components_to_parts():
    """Migrate components to parts-based system"""
    print("🔄 Starting migration of components to parts...")
    
    app = create_app()
    with app.app_context():
        # Get all existing components
        components = Component.query.all()
        print(f"Found {len(components)} components to migrate")
        
        migrated_parts = {}
        migrated_count = 0
        
        for component in components:
            try:
                # Create a unique key for the part
                part_key = (
                    component.part_number or f"COMP-{component.component_id}",
                    component.component_name,
                    component.unit_price
                )
                
                # Check if we already created this part
                if part_key not in migrated_parts:
                    # Create new part
                    part = Parts(
                        category='General',
                        manufacturer='Unknown',
                        part_number=component.part_number or f"COMP-{component.component_id}",
                        description=component.component_name,
                        price=component.unit_price,
                        effective_date=datetime.now().date(),
                        created_at=component.created_at,
                        updated_at=component.updated_at
                    )
                    db.session.add(part)
                    db.session.flush()  # Get the part_id
                    migrated_parts[part_key] = part
                    print(f"  📦 Created part: {part.description} (ID: {part.part_id})")
                else:
                    part = migrated_parts[part_key]
                
                # Create assembly part link
                assembly_part = AssemblyPart(
                    assembly_id=component.assembly_id,
                    part_id=part.part_id,
                    quantity=component.quantity,
                    unit_of_measure=component.unit_of_measure,
                    sort_order=component.sort_order,
                    notes=component.description,
                    created_at=component.created_at,
                    updated_at=component.updated_at
                )
                db.session.add(assembly_part)
                migrated_count += 1
                
                # Migrate price history
                price_history_records = PriceHistory.query.filter_by(component_id=component.component_id).all()
                for ph in price_history_records:
                    parts_ph = PartsPriceHistory(
                        part_id=part.part_id,
                        old_price=ph.old_price,
                        new_price=ph.new_price,
                        changed_at=ph.changed_at,
                        changed_reason=f"Migrated from component: {ph.changed_reason}"
                    )
                    db.session.add(parts_ph)
                
            except Exception as e:
                print(f"  ❌ Error migrating component {component.component_id}: {e}")
                db.session.rollback()
                continue
        
        try:
            db.session.commit()
            print(f"✅ Migration completed successfully!")
            print(f"  📊 Migrated {migrated_count} component links")
            print(f"  🏷️  Created {len(migrated_parts)} unique parts")
            
            # Verification
            parts_count = Parts.query.count()
            assembly_parts_count = AssemblyPart.query.count()
            print(f"  ✅ Verification: {parts_count} parts, {assembly_parts_count} assembly parts")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False
    
    return True

def main():
    """Main migration function"""
    print("🚀 Starting Components to Parts Migration")
    print("=" * 50)
    
    # Step 1: Backup database
    backup_file = backup_database()
    
    # Step 2: Create new tables
    app = create_app()
    with app.app_context():
        create_tables()
        
        # Step 3: Migrate data
        success = migrate_components_to_parts()
        
        if success:
            print("\n🎉 Migration completed successfully!")
            print("\n⚠️  IMPORTANT NEXT STEPS:")
            print("1. Test the application thoroughly")
            print("2. Verify all estimates display correctly")
            print("3. Check that parts can be added/edited in assemblies")
            print("4. Once confirmed working, you can drop the old tables:")
            print("   - DROP TABLE components;")
            print("   - DROP TABLE price_history;")
            if backup_file:
                print(f"5. Your backup is saved as: {backup_file}")
        else:
            print("\n💥 Migration failed!")
            if backup_file:
                print(f"You can restore from backup: {backup_file}")

if __name__ == "__main__":
    main()
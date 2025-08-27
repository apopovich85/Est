#!/usr/bin/env python3

from app import create_app
from app.models import db, AssemblyCategory

def main():
    app = create_app()
    with app.app_context():
        # Create the assembly_categories table
        db.create_all()
        
        # Check if categories already exist
        existing_count = AssemblyCategory.query.count()
        if existing_count > 0:
            print(f"Categories table already has {existing_count} entries. Skipping initial data.")
            return
            
        # Initial categories with descriptions
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
            {'code': 'WW', 'name': 'Water/Wastewater', 'description': 'Water and wastewater treatment systems', 'sort_order': 130},
            {'code': 'INST-PRS', 'name': 'Pressure Instrumentation', 'description': 'Pressure measurement instrumentation', 'sort_order': 140},
            {'code': 'LVM', 'name': 'Low Voltage Motor', 'description': 'Low voltage motor controls', 'sort_order': 150},
            {'code': 'SG', 'name': 'Switch Gear', 'description': 'Switchgear and load centers', 'sort_order': 160},
            {'code': 'LVST', 'name': 'Low Voltage Starter', 'description': 'Low voltage motor starters', 'sort_order': 170},
            {'code': 'HS', 'name': 'Hand Switch', 'description': 'Manual switches and controls', 'sort_order': 180},
        ]
        
        # Add categories to database
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
        print(f"Successfully created {len(initial_categories)} assembly categories")
        
        # List all categories
        categories = AssemblyCategory.get_active_categories()
        print("\nCreated categories:")
        for cat in categories:
            print(f"  {cat.code}: {cat.name}")

if __name__ == '__main__':
    main()
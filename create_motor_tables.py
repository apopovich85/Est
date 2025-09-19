#!/usr/bin/env python3
"""
Database migration script for Motor Management System
Creates new tables: t_motors, t_vfdtype, t_necamptable, t_techdata
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import VFDType, NECAmpTable, TechData, Motor
import pandas as pd

def create_motor_tables():
    """Create all motor-related tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating motor management tables...")
        
        # Create all tables
        db.create_all()
        
        print("SUCCESS: Tables created successfully")
        return True

def populate_vfd_types():
    """Populate VFD types table with initial data"""
    app = create_app()
    
    with app.app_context():
        print("Populating VFD types...")
        
        vfd_types = [
            {'type_name': '755', 'manufacturer': 'Allen-Bradley', 'sort_order': 1},
            {'type_name': '755TS', 'manufacturer': 'Allen-Bradley', 'sort_order': 2},
        ]
        
        for vfd_data in vfd_types:
            existing = VFDType.query.filter_by(type_name=vfd_data['type_name']).first()
            if not existing:
                vfd_type = VFDType(**vfd_data)
                db.session.add(vfd_type)
                print(f"  Added VFD type: {vfd_data['type_name']}")
            else:
                print(f"  VFD type already exists: {vfd_data['type_name']}")
        
        db.session.commit()
        print("SUCCESS: VFD types populated")
        return True

def populate_nec_amp_table():
    """Populate NEC amp table from Excel data"""
    app = create_app()
    
    with app.app_context():
        print("Populating NEC amp table from Excel...")
        
        try:
            # Read NECMtrFLC worksheet
            df = pd.read_excel('ImportData/E&A_Est-v0.2A.xlsm', 
                             sheet_name='NECMtrFLC', header=None, skiprows=5)
            
            # Clean up the data - columns should be: HP, 115V, 200V, 208V, 230V, 460V, 575V, 2300V
            df = df.iloc[:, 0:8]  # Take first 8 columns
            df.columns = ['hp', 'voltage_115', 'voltage_200', 'voltage_208', 
                         'voltage_230', 'voltage_460', 'voltage_575', 'voltage_2300']
            
            # Remove rows where HP is not a number
            df = df[pd.to_numeric(df['hp'], errors='coerce').notna()]
            
            # Convert HP to numeric
            df['hp'] = pd.to_numeric(df['hp'])
            
            # Replace '—' and 'Ω' with None for missing values
            for col in df.columns[1:]:
                df[col] = df[col].replace(['—', 'Ω', '–', '�'], None)
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"Found {len(df)} HP ratings to import")
            
            # Import into database
            for _, row in df.iterrows():
                existing = NECAmpTable.query.filter_by(hp=row['hp']).first()
                if not existing:
                    nec_record = NECAmpTable(
                        hp=row['hp'],
                        voltage_115=row['voltage_115'],
                        voltage_200=row['voltage_200'],
                        voltage_208=row['voltage_208'],
                        voltage_230=row['voltage_230'],
                        voltage_460=row['voltage_460'],
                        voltage_575=row['voltage_575'],
                        voltage_2300=row['voltage_2300']
                    )
                    db.session.add(nec_record)
                    print(f"  Added NEC data for {row['hp']}HP")
                else:
                    print(f"  NEC data already exists for {row['hp']}HP")
            
            db.session.commit()
            print("SUCCESS: NEC amp table populated")
            
        except Exception as e:
            print(f"Error populating NEC amp table: {e}")
            db.session.rollback()
            return False
            
        return True

def populate_tech_data():
    """Populate tech data for existing VFD parts from Excel PartsDB"""
    app = create_app()
    
    with app.app_context():
        print("Populating tech data from Excel PartsDB...")
        
        try:
            # Read PartsDB worksheet
            df = pd.read_excel('ImportData/E&A_Est-v0.2A.xlsm', 
                             sheet_name='PartsDB', header=0)
            
            # Filter for VFD parts only
            vfd_df = df[df['Title'] == 'VFD'].copy()
            
            print(f"Found {len(vfd_df)} VFD parts in Excel PartsDB")
            
            # Map Excel columns to our database
            for _, row in vfd_df.iterrows():
                catalog_number = row.get('Catalog')
                if pd.isna(catalog_number):
                    continue
                    
                # Find matching part in our parts table by part_number or description
                from app.models import Parts
                part = Parts.query.filter(
                    (Parts.part_number == catalog_number) |
                    (Parts.description.contains(catalog_number))
                ).first()
                
                if part:
                    # Check if tech data already exists
                    existing_tech = TechData.query.filter_by(part_id=part.part_id).first()
                    if not existing_tech:
                        tech_data = TechData(
                            part_id=part.part_id,
                            heat_loss_w=row.get('Heat Loss') if pd.notna(row.get('Heat Loss')) else None,
                            width_in=row.get('DimWidth') if pd.notna(row.get('DimWidth')) else None,
                            height_in=row.get('DimHeight') if pd.notna(row.get('DimHeight')) else None,
                            length_in=row.get('DimDepth.') if pd.notna(row.get('DimDepth.')) else None,
                            frame_size=row.get('Frame') if pd.notna(row.get('Frame')) else None,
                            input_current=row.get('InputCurrent') if pd.notna(row.get('InputCurrent')) else None
                        )
                        db.session.add(tech_data)
                        print(f"  Added tech data for part: {catalog_number}")
                    else:
                        print(f"  Tech data already exists for: {catalog_number}")
                else:
                    print(f"  Part not found in database: {catalog_number}")
            
            db.session.commit()
            print("SUCCESS: Tech data populated")
            
        except Exception as e:
            print(f"Error populating tech data: {e}")
            db.session.rollback()
            return False
            
        return True

def main():
    """Run all migration steps"""
    print("=== Motor Management System Database Migration ===")
    
    steps = [
        ("Creating tables", create_motor_tables),
        ("Populating VFD types", populate_vfd_types),
        ("Populating NEC amp table", populate_nec_amp_table),
        ("Populating tech data", populate_tech_data)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            if not step_func():
                print(f"FAILED: {step_name}")
                return False
        except Exception as e:
            print(f"ERROR in {step_name}: {e}")
            return False
    
    print("\nSUCCESS: Motor management system migration completed successfully!")
    return True

if __name__ == "__main__":
    main()
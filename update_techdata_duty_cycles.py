"""
Update t_techdata table to include Normal Duty and Heavy Duty input current columns
and populate data from PowerFlex CSV file
"""
from app import create_app, db
from app.models import Parts, TechData
import csv
from decimal import Decimal

app = create_app()

def update_techdata_schema():
    """Add ND and HD input current columns to t_techdata table"""
    with app.app_context():
        # Add new columns using raw SQL
        try:
            # Check if columns exist
            result = db.session.execute(db.text("""
                SELECT COUNT(*)
                FROM pragma_table_info('t_techdata')
                WHERE name IN ('input_current_nd', 'input_current_hd')
            """))
            count = result.scalar()

            if count < 2:
                print("Adding input_current_nd and input_current_hd columns to t_techdata...")

                # Add Normal Duty input current column
                db.session.execute(db.text("""
                    ALTER TABLE t_techdata
                    ADD COLUMN input_current_nd NUMERIC(8, 3)
                """))

                # Add Heavy Duty input current column
                db.session.execute(db.text("""
                    ALTER TABLE t_techdata
                    ADD COLUMN input_current_hd NUMERIC(8, 3)
                """))

                db.session.commit()
                print("[OK] Columns added successfully")
            else:
                print("[OK] Columns already exist")

        except Exception as e:
            print(f"Error updating schema: {e}")
            db.session.rollback()
            raise

def load_powerflex_data():
    """Load PowerFlex data from CSV and update/create TechData records"""
    with app.app_context():
        csv_file = 'uploads/powerflex_750ts_.csv'

        # Read CSV data
        powerflex_data = {}
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process Normal Duty data
                nd_cat_no = row.get('Normal Duty Cat No', '').strip()
                nd_input_amps = row.get('Normal Duty Cont AC Input Amps', '').strip()

                if nd_cat_no and nd_input_amps:
                    if nd_cat_no not in powerflex_data:
                        powerflex_data[nd_cat_no] = {}
                    powerflex_data[nd_cat_no]['nd_amps'] = nd_input_amps

                # Process Heavy Duty data - handle column with space in name
                hd_cat_no = row.get('Heavy Duty Cat No', '').strip()
                # Try both possible column names due to trailing space
                hd_input_amps = row.get(' Heavy Duty Cont AC Input Amps', '').strip() or row.get('Heavy Duty Cont AC Input Amps', '').strip()

                if hd_cat_no and hd_input_amps:
                    if hd_cat_no not in powerflex_data:
                        powerflex_data[hd_cat_no] = {}
                    powerflex_data[hd_cat_no]['hd_amps'] = hd_input_amps

        print(f"Loaded {len(powerflex_data)} unique catalog numbers from CSV")

        # Update/create TechData records
        updated_count = 0
        created_count = 0
        missing_parts = []

        for cat_no, amps_data in powerflex_data.items():
            # Find the part by catalog number (part_number)
            part = Parts.query.filter_by(part_number=cat_no).first()

            if not part:
                missing_parts.append(cat_no)
                continue

            # Check if TechData exists for this part
            tech_data = TechData.query.filter_by(part_id=part.part_id).first()

            if tech_data:
                # Update existing record
                if 'nd_amps' in amps_data:
                    tech_data.input_current_nd = Decimal(amps_data['nd_amps'])
                if 'hd_amps' in amps_data:
                    tech_data.input_current_hd = Decimal(amps_data['hd_amps'])
                updated_count += 1
                print(f"Updated {cat_no}: ND={amps_data.get('nd_amps', 'N/A')}A, HD={amps_data.get('hd_amps', 'N/A')}A")
            else:
                # Create new TechData record
                tech_data = TechData(
                    part_id=part.part_id,
                    input_current_nd=Decimal(amps_data['nd_amps']) if 'nd_amps' in amps_data else None,
                    input_current_hd=Decimal(amps_data['hd_amps']) if 'hd_amps' in amps_data else None
                )
                db.session.add(tech_data)
                created_count += 1
                print(f"Created {cat_no}: ND={amps_data.get('nd_amps', 'N/A')}A, HD={amps_data.get('hd_amps', 'N/A')}A")

        db.session.commit()

        print(f"\n[OK] Updated {updated_count} existing TechData records")
        print(f"[OK] Created {created_count} new TechData records")

        if missing_parts:
            print(f"\n[WARNING] {len(missing_parts)} catalog numbers not found in Parts table:")
            for cat_no in missing_parts[:10]:  # Show first 10
                print(f"  - {cat_no}")
            if len(missing_parts) > 10:
                print(f"  ... and {len(missing_parts) - 10} more")

def migrate_existing_input_current():
    """Migrate existing input_current values to input_current_nd (assume Normal Duty)"""
    with app.app_context():
        tech_data_records = TechData.query.filter(TechData.input_current.isnot(None)).all()

        migrated_count = 0
        for td in tech_data_records:
            if td.input_current and not td.input_current_nd:
                td.input_current_nd = td.input_current
                migrated_count += 1

        db.session.commit()
        print(f"[OK] Migrated {migrated_count} existing input_current values to input_current_nd")

if __name__ == '__main__':
    print("Starting TechData table update...\n")

    # Step 1: Update schema
    print("Step 1: Updating database schema")
    update_techdata_schema()

    # Step 2: Migrate existing data
    print("\nStep 2: Migrating existing input_current values")
    migrate_existing_input_current()

    # Step 3: Load PowerFlex data
    print("\nStep 3: Loading PowerFlex data from CSV")
    load_powerflex_data()

    print("\n[OK] Migration complete!")

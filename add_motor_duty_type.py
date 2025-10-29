"""
Add duty_type column to t_motors and motor_revisions tables
"""
from app import create_app, db

app = create_app()

def add_duty_type_columns():
    """Add duty_type column to motors and motor_revisions tables"""
    with app.app_context():
        try:
            # Check if column exists in t_motors
            result = db.session.execute(db.text("""
                SELECT COUNT(*)
                FROM pragma_table_info('t_motors')
                WHERE name = 'duty_type'
            """))
            count = result.scalar()

            if count == 0:
                print("Adding duty_type column to t_motors...")
                db.session.execute(db.text("""
                    ALTER TABLE t_motors
                    ADD COLUMN duty_type VARCHAR(2) DEFAULT 'ND'
                """))
                db.session.commit()
                print("[OK] duty_type column added to t_motors")
            else:
                print("[OK] duty_type column already exists in t_motors")

            # Check if column exists in motor_revisions
            result = db.session.execute(db.text("""
                SELECT COUNT(*)
                FROM pragma_table_info('motor_revisions')
                WHERE name = 'duty_type'
            """))
            count = result.scalar()

            if count == 0:
                print("Adding duty_type column to motor_revisions...")
                db.session.execute(db.text("""
                    ALTER TABLE motor_revisions
                    ADD COLUMN duty_type VARCHAR(2)
                """))
                db.session.commit()
                print("[OK] duty_type column added to motor_revisions")
            else:
                print("[OK] duty_type column already exists in motor_revisions")

        except Exception as e:
            print(f"Error adding columns: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    print("Adding duty_type columns to motor tables...\n")
    add_duty_type_columns()
    print("\n[OK] Migration complete!")

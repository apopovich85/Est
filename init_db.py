# ==================================================
# init_db.py (Database initialization script)
#!/usr/bin/env python3
"""Database initialization script"""
import sys
from app import create_app, db
from app.models import Project, Estimate, Assembly, Component, PriceHistory, User

def init_database():
    """Initialize the database with tables and sample data"""
    app = create_app()

    with app.app_context():
        # Drop all tables and recreate
        print("Creating database tables...")
        db.drop_all()
        db.create_all()

        # Create sample user
        print("Creating sample user...")
        user = User(
            username='admin',
            email='admin@company.com',
            full_name='System Administrator',
            role='Admin'
        )
        db.session.add(user)
        db.session.commit()

        # Create sample project
        print("Creating sample project...")
        project = Project(
            project_name='Sample Office Building',
            client_name='ABC Construction Corp',
            description='Modern office building with sustainable features',
            status='Draft'
        )
        db.session.add(project)
        db.session.commit()

        # Create sample estimate
        estimate = Estimate(
            project_id=project.project_id,
            estimate_number='EST-20240101-SAMPLE01',
            estimate_name='Main Building Estimate',
            description='Primary estimate for office building construction'
        )
        db.session.add(estimate)
        db.session.commit()

        # Create sample assembly
        assembly = Assembly(
            estimate_id=estimate.estimate_id,
            assembly_name='Electrical System',
            description='Complete electrical installation including wiring, panels, and fixtures'
        )
        db.session.add(assembly)
        db.session.commit()

        # Create sample components
        components_data = [
            {
                'component_name': 'Main Electrical Panel',
                'description': '200A main breaker panel',
                'part_number': 'SQ-QO130M200',
                'unit_price': 450.00,
                'quantity': 1,
                'unit_of_measure': 'EA'
            },
            {
                'component_name': '12 AWG THHN Wire',
                'description': 'Copper building wire',
                'part_number': 'THHN-12-BLK',
                'unit_price': 0.85,
                'quantity': 2500,
                'unit_of_measure': 'FT'
            },
            {
                'component_name': 'LED Recessed Lights',
                'description': '6" LED downlights, 3000K',
                'part_number': 'HALO-RL560',
                'unit_price': 35.50,
                'quantity': 48,
                'unit_of_measure': 'EA'
            }
        ]

        for comp_data in components_data:
            component = Component(
                assembly_id=assembly.assembly_id,
                **comp_data
            )
            db.session.add(component)

        db.session.commit()

        print("Database initialized successfully!")
        print(f"Sample project created: {project.project_name}")
        print(f"Sample estimate created: {estimate.estimate_name}")
        print("You can now run the application with: python app.py")

if __name__ == '__main__':
    init_database()
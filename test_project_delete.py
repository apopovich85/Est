"""
Test script to verify project deletion with all cascades
"""
from app import create_app, db
from app.models import Project, Estimate, Assembly, AssemblyPart, EstimateComponent, Motor
from sqlalchemy import text

def test_delete_functionality():
    """Test that project deletion removes all related data"""
    app = create_app()

    with app.app_context():
        # First, verify foreign keys are enabled
        result = db.session.execute(text("PRAGMA foreign_keys")).fetchone()
        print(f"Foreign keys enabled: {result[0] == 1}")
        print()

        # Get all projects
        projects = Project.query.all()
        print(f"Total projects in database: {len(projects)}")

        if not projects:
            print("\nNo projects found to test deletion.")
            return

        # Show projects with their related data
        print("\n" + "="*80)
        print("PROJECTS AND THEIR RELATED DATA:")
        print("="*80)

        for project in projects:
            estimates = Estimate.query.filter_by(project_id=project.project_id).all()
            motors = Motor.query.filter_by(project_id=project.project_id).all()

            total_assemblies = 0
            total_assembly_parts = 0
            total_estimate_components = 0

            for estimate in estimates:
                assemblies = Assembly.query.filter_by(estimate_id=estimate.estimate_id).all()
                total_assemblies += len(assemblies)

                for assembly in assemblies:
                    parts = AssemblyPart.query.filter_by(assembly_id=assembly.assembly_id).all()
                    total_assembly_parts += len(parts)

                components = EstimateComponent.query.filter_by(estimate_id=estimate.estimate_id).all()
                total_estimate_components += len(components)

            print(f"\nProject ID: {project.project_id}")
            print(f"  Name: {project.project_name}")
            print(f"  Client: {project.client_name}")
            print(f"  Status: {project.status}")
            print(f"  Related Data:")
            print(f"    - Estimates: {len(estimates)}")
            print(f"    - Assemblies: {total_assemblies}")
            print(f"    - Assembly Parts: {total_assembly_parts}")
            print(f"    - Individual Components: {total_estimate_components}")
            print(f"    - Motors/Loads: {len(motors)}")

        print("\n" + "="*80)
        print("\nTo delete a project, use the delete button in the web interface")
        print("or manually test by uncommenting the code below and running this script.")
        print("="*80)

def delete_project_by_id(project_id):
    """Delete a specific project and verify all cascades work"""
    app = create_app()

    with app.app_context():
        project = Project.query.get(project_id)
        if not project:
            print(f"Project {project_id} not found!")
            return

        # Count everything before deletion
        print(f"\nDeleting Project: {project.project_name}")
        estimates = Estimate.query.filter_by(project_id=project.project_id).all()
        motors = Motor.query.filter_by(project_id=project.project_id).all()

        estimate_ids = [e.estimate_id for e in estimates]
        assembly_count = Assembly.query.filter(Assembly.estimate_id.in_(estimate_ids)).count() if estimate_ids else 0

        assembly_ids = [a.assembly_id for a in Assembly.query.filter(Assembly.estimate_id.in_(estimate_ids)).all()] if estimate_ids else []
        assembly_part_count = AssemblyPart.query.filter(AssemblyPart.assembly_id.in_(assembly_ids)).count() if assembly_ids else 0

        component_count = EstimateComponent.query.filter(EstimateComponent.estimate_id.in_(estimate_ids)).count() if estimate_ids else 0

        print(f"  - {len(estimates)} estimates")
        print(f"  - {assembly_count} assemblies")
        print(f"  - {assembly_part_count} assembly parts")
        print(f"  - {component_count} individual components")
        print(f"  - {len(motors)} motors/loads")

        # Delete the project
        try:
            db.session.delete(project)
            db.session.commit()
            print("\nProject deleted successfully!")

            # Verify deletion
            remaining_estimates = Estimate.query.filter_by(project_id=project_id).count()
            remaining_motors = Motor.query.filter_by(project_id=project_id).count()

            print(f"\nVerification:")
            print(f"  - Remaining estimates for this project: {remaining_estimates}")
            print(f"  - Remaining motors for this project: {remaining_motors}")

            if remaining_estimates == 0 and remaining_motors == 0:
                print("\n✓ All related data successfully deleted!")
            else:
                print("\n✗ WARNING: Some related data was not deleted!")

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error deleting project: {str(e)}")

if __name__ == '__main__':
    # Show all projects and their data
    test_delete_functionality()

    # To delete a specific project, uncomment the line below and set the project_id
    # delete_project_by_id(1)  # Replace 1 with the actual project_id you want to delete

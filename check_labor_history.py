from app import create_app, db
from app.models import Project, Estimate, EstimateRevision
import sys

app = create_app()
with app.app_context():
    # Search for project by name
    project = Project.query.filter(
        (Project.project_name.like('%p20764%')) |
        (Project.project_name.like('%20764%'))
    ).first()

    if not project:
        print('Project p20764 not found')
        # Try listing all projects to help find it
        projects = Project.query.all()
        print(f'\nAvailable projects ({len(projects)}):')
        for p in projects[:20]:
            print(f'  ID: {p.project_id} - {p.project_name} ({p.client_name})')
        sys.exit(0)

    print(f'Found Project: {project.project_name}')
    print(f'Project ID: {project.project_id}')
    print()

    # Get all estimates for this project
    estimates = Estimate.query.filter_by(project_id=project.project_id).all()
    print(f'Found {len(estimates)} estimate(s):')
    print()

    for est in estimates:
        print(f'Estimate: {est.estimate_name}')
        print(f'  ID: {est.estimate_id}')
        print(f'  Estimate Number: {est.estimate_number}')
        print(f'  Revision: {est.revision_number}')
        print(f'  Engineering Hours: {est.engineering_hours or 0}')
        print(f'  Panel Shop Hours: {est.panel_shop_hours or 0}')
        print(f'  Machine Assembly Hours: {est.machine_assembly_hours or 0}')
        print(f'  Total Labor Cost: ${est.total_labor_cost:,.2f}')
        print(f'  Created At: {est.created_at}')
        print(f'  Updated At: {est.updated_at}')
        print()

        # Check for revisions
        revisions = EstimateRevision.query.filter_by(estimate_id=est.estimate_id).order_by(EstimateRevision.created_at).all()
        if revisions:
            print(f'  Revision History ({len(revisions)} revisions):')
            for rev in revisions:
                print(f'    Rev {rev.revision_number} - Created: {rev.created_at}')
                print(f'      Engineering Hours: {rev.engineering_hours or 0}')
                print(f'      Panel Shop Hours: {rev.panel_shop_hours or 0}')
                print(f'      Machine Assembly Hours: {rev.machine_assembly_hours or 0}')
                print(f'      Total Labor Cost: ${rev.total_labor_cost:,.2f}')
                print(f'      Changes: {rev.changes_summary}')
                if rev.detailed_changes:
                    print(f'      Details: {rev.detailed_changes}')
                print(f'      Created By: {rev.created_by}')
                print()
        else:
            print('  No revision history found')
            print()

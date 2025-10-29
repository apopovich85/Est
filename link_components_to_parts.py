"""
Script to link EstimateComponent records to their corresponding Parts records
based on matching part_number.
"""
from app import create_app, db
from app.models import EstimateComponent, Parts

app = create_app()
ctx = app.app_context()
ctx.push()

# Get all individual components that don't have a part_id but do have a part_number
components = EstimateComponent.query.filter(
    EstimateComponent.part_id.is_(None),
    EstimateComponent.part_number.isnot(None),
    EstimateComponent.part_number != ''
).all()

print(f'Found {len(components)} components to potentially link\n')

linked_count = 0
not_found_count = 0
skipped_count = 0

for component in components:
    # Try to find matching part
    part = Parts.query.filter_by(part_number=component.part_number).first()

    if part:
        print(f'Linking: {component.component_name[:50]}')
        print(f'  Part Number: {component.part_number}')
        print(f'  -> Part ID: {part.part_id}, Category: {part.category}')

        # Link the component to the part
        component.part_id = part.part_id
        linked_count += 1
    else:
        print(f'NOT FOUND: {component.component_name[:50]}')
        print(f'  Part Number: {component.part_number}')
        not_found_count += 1

    print()

# Commit the changes
try:
    db.session.commit()
    print(f'\n[SUCCESS] Linked {linked_count} components to parts')
    if not_found_count > 0:
        print(f'[WARNING] {not_found_count} components could not be linked (no matching part found)')
except Exception as e:
    db.session.rollback()
    print(f'\n[ERROR] Error committing changes: {e}')

ctx.pop()

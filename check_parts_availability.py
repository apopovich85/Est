from app import create_app, db
from app.models import EstimateComponent, Parts

app = create_app()
ctx = app.app_context()
ctx.push()

# Get components from estimate 98
components = EstimateComponent.query.filter_by(estimate_id=98).all()

print(f'Checking if components have matching parts in the Parts table...\n')

for c in components:
    print(f'Component: {c.component_name[:60]}')
    print(f'  Part Number: {c.part_number}')

    # Try to find matching part by part_number
    if c.part_number:
        matching_parts = Parts.query.filter_by(part_number=c.part_number).all()
        if matching_parts:
            print(f'  [+] Found {len(matching_parts)} matching part(s) in Parts table:')
            for p in matching_parts:
                print(f'    - Part ID: {p.part_id}, Category: {p.category}, Manufacturer: {p.manufacturer}')
        else:
            print(f'  [-] No matching part found in Parts table')
    else:
        print(f'  [-] No part_number set on component')

    print()

ctx.pop()

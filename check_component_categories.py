from app import create_app, db
from app.models import EstimateComponent, Parts

app = create_app()
ctx = app.app_context()
ctx.push()

# Get components from estimate 98
components = EstimateComponent.query.filter_by(estimate_id=98).all()

print(f'Found {len(components)} individual components in estimate 98\n')

for c in components:
    print(f'Component: {c.component_name}')
    print(f'  part_id: {c.part_id}')
    print(f'  component.category (direct): {c.category}')
    print(f'  has part relationship: {c.part is not None}')

    if c.part:
        print(f'  part.part_number: {c.part.part_number}')
        print(f'  part.category_id: {c.part.category_id}')
        print(f'  part.category (property): {c.part.category}')
        if c.part.part_category:
            print(f'  part.part_category.name: {c.part.part_category.name}')
    print()

ctx.pop()

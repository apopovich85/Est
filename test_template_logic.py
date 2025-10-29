"""
Test the template logic for displaying categories
"""
from app import create_app, db
from app.models import EstimateComponent

app = create_app()
ctx = app.app_context()
ctx.push()

# Get components from estimate 98
components = EstimateComponent.query.filter_by(estimate_id=98).limit(5).all()

print('Testing template logic: {% set display_category = component.part.category if component.part else component.category %}\n')

for component in components:
    # Simulate template logic
    display_category = component.part.category if component.part else component.category

    print(f'Component: {component.component_name[:50]}')
    print(f'  Template will display: "{display_category}"')
    print()

ctx.pop()

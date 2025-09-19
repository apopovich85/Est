from app import create_app
from app.models import Parts, TechData

app = create_app()
with app.app_context():
    print('Testing VFD parts and ratings:')
    
    # Check VFD parts with ratings
    vfd_parts = Parts.query.filter(
        Parts.description.contains('755TS')
    ).limit(10).all()
    
    print(f'Found {len(vfd_parts)} 755TS VFD parts:')
    for vfd in vfd_parts:
        print(f'  {vfd.part_number} - Rating: {vfd.rating}A - Price: ${vfd.current_price:.2f}')
        if hasattr(vfd, 'tech_data') and vfd.tech_data:
            if isinstance(vfd.tech_data, list) and len(vfd.tech_data) > 0:
                td = vfd.tech_data[0]
                print(f'    Tech Data: Heat Loss: {td.heat_loss_w}W, Width: {td.width_in} inches')
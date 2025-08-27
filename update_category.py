#!/usr/bin/env python3

from app import create_app
from app.models import StandardAssembly, db

def main():
    app = create_app()
    with app.app_context():
        # Update the Test assembly category
        assembly = StandardAssembly.query.get(1)
        if assembly:
            print(f'Found assembly: {assembly.name}')
            print(f'Current category: {assembly.category}')
            
            # Update to VFD category
            assembly.category = 'VFD'
            db.session.commit()
            
            print(f'Updated category to: {assembly.category}')
        else:
            print('Assembly with ID 1 not found')

if __name__ == '__main__':
    main()
from decimal import Decimal
import uuid
from datetime import datetime

def generate_estimate_number():
    """Generate a unique estimate number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"EST-{timestamp}-{unique_id}"

def format_currency(amount):
    """Format amount as currency string"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"

def copy_estimate_structure(source_estimate_id, target_project_id, new_estimate_name=None):
    """Copy an entire estimate structure to a new project"""
    from app.models import Estimate, Assembly, Component
    from app import db
    
    # Get source estimate
    source_estimate = Estimate.query.get(source_estimate_id)
    if not source_estimate:
        raise ValueError("Source estimate not found")
    
    # Create new estimate
    new_estimate = Estimate(
        project_id=target_project_id,
        estimate_number=generate_estimate_number(),
        estimate_name=new_estimate_name or f"Copy of {source_estimate.estimate_name}",
        description=source_estimate.description
    )
    db.session.add(new_estimate)
    db.session.flush()  # Get the new estimate ID
    
    # Copy assemblies and components
    for assembly in source_estimate.assemblies:
        new_assembly = Assembly(
            estimate_id=new_estimate.estimate_id,
            assembly_name=assembly.assembly_name,
            description=assembly.description,
            sort_order=assembly.sort_order
        )
        db.session.add(new_assembly)
        db.session.flush()  # Get the new assembly ID
        
        for component in assembly.components:
            new_component = Component(
                assembly_id=new_assembly.assembly_id,
                component_name=component.component_name,
                description=component.description,
                part_number=component.part_number,
                unit_price=component.unit_price,
                quantity=component.quantity,
                unit_of_measure=component.unit_of_measure,
                sort_order=component.sort_order
            )
            db.session.add(new_component)
    
    db.session.commit()
    return new_estimate
    }
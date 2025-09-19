from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Assembly, Estimate, AssemblyPart
from app import db, csrf

bp = Blueprint('assemblies', __name__)

@bp.route('/create/<int:estimate_id>', methods=['GET', 'POST'])
def create_assembly(estimate_id):
    """Create a new assembly for an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    if request.method == 'POST':
        try:
            # Get the highest sort order for this estimate
            max_sort = db.session.query(db.func.max(Assembly.sort_order))\
                .filter_by(estimate_id=estimate_id).scalar() or 0
            
            assembly = Assembly(
                estimate_id=estimate_id,
                assembly_name=request.form['assembly_name'],
                description=request.form.get('description', ''),
                sort_order=max_sort + 1
            )
            
            db.session.add(assembly)
            db.session.commit()
            
            flash(f'Assembly "{assembly.assembly_name}" created successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating assembly: {str(e)}', 'error')
    
    return render_template('assemblies/create.html', estimate=estimate)

@bp.route('/manage_hours/<int:estimate_id>')
def manage_hours(estimate_id):
    """Manage time estimates for all assemblies in an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    assemblies = Assembly.query.filter_by(estimate_id=estimate_id).order_by(Assembly.sort_order).all()
    
    return render_template('assemblies/manage_hours.html', estimate=estimate, assemblies=assemblies)

@bp.route('/update_hours/<int:estimate_id>', methods=['POST'])
@csrf.exempt
def update_hours(estimate_id):
    """Update time estimates for multiple assemblies"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        # Process each assembly's time data
        for assembly in estimate.assemblies:
            assembly_id = assembly.assembly_id
            
            # Get form data for this assembly
            engineering_hours = request.form.get(f'engineering_hours_{assembly_id}', 0)
            panel_shop_hours = request.form.get(f'panel_shop_hours_{assembly_id}', 0)
            machine_assembly_hours = request.form.get(f'machine_assembly_hours_{assembly_id}', 0)
            estimated_by = request.form.get(f'estimated_by_{assembly_id}', '')
            time_estimate_notes = request.form.get(f'time_estimate_notes_{assembly_id}', '')
            
            # Update assembly with new values
            assembly.engineering_hours = float(engineering_hours or 0)
            assembly.panel_shop_hours = float(panel_shop_hours or 0)
            assembly.machine_assembly_hours = float(machine_assembly_hours or 0)
            assembly.estimated_by = estimated_by
            assembly.time_estimate_notes = time_estimate_notes
        
        db.session.commit()
        flash('Time estimates updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating time estimates: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))

@bp.route('/delete/<int:assembly_id>', methods=['POST'])
@csrf.exempt
def delete_assembly(assembly_id):
    """Delete an assembly and all its components"""
    assembly = Assembly.query.get_or_404(assembly_id)
    estimate_id = assembly.estimate_id
    assembly_name = assembly.assembly_name
    
    try:
        db.session.delete(assembly)
        db.session.commit()
        flash(f'Assembly "{assembly_name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting assembly: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))

@bp.route('/<int:assembly_id>/update-quantity', methods=['POST'])
@csrf.exempt
def update_assembly_quantity(assembly_id):
    """Update assembly quantity and adjust all component quantities proportionally"""
    assembly = Assembly.query.get_or_404(assembly_id)
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400
    
    new_quantity = request.json.get('quantity')
    if not new_quantity or new_quantity < 1:
        return jsonify({'success': False, 'error': 'Quantity must be at least 1'}), 400
    
    try:
        old_quantity = float(assembly.quantity or 1.0)
        new_quantity = float(new_quantity)
        
        # Only update if the assembly was created from a standard assembly
        if not assembly.standard_assembly_id:
            return jsonify({'success': False, 'error': 'Can only adjust quantity for standard assemblies'}), 400
        
        # Update assembly quantity
        assembly.quantity = new_quantity
        
        # Update assembly name to reflect quantity
        base_name = assembly.assembly_name
        # Remove existing quantity suffix if present
        if ' (x' in base_name:
            base_name = base_name.split(' (x')[0]
        
        if new_quantity > 1:
            assembly.assembly_name = f"{base_name} (x{int(new_quantity) if new_quantity.is_integer() else new_quantity})"
        else:
            assembly.assembly_name = base_name
        
        # Get original quantities from standard assembly and multiply by new assembly quantity
        from app.models import StandardAssemblyComponent
        standard_components = StandardAssemblyComponent.query.filter_by(
            standard_assembly_id=assembly.standard_assembly_id
        ).all()
        
        # Create a mapping of part_id to original quantity
        original_quantities = {}
        for std_component in standard_components:
            original_quantities[std_component.part_id] = float(std_component.quantity)
        
        # Update all component quantities based on original quantities * new assembly quantity
        for component in assembly.assembly_parts:
            if component.part_id in original_quantities:
                original_qty = original_quantities[component.part_id]
                component.quantity = original_qty * new_quantity
            else:
                # Fallback: if we can't find original quantity, use current quantity adjusted proportionally
                component.quantity = float(component.quantity) * (new_quantity / old_quantity)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Assembly quantity updated to {new_quantity}',
            'new_quantity': new_quantity,
            'assembly_name': assembly.assembly_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:assembly_id>/refresh-to-active', methods=['POST'])
@csrf.exempt
def refresh_assembly_to_active(assembly_id):
    """Refresh assembly to current active version of standard assembly"""
    assembly = Assembly.query.get_or_404(assembly_id)
    
    if not assembly.standard_assembly_id:
        return jsonify({'success': False, 'error': 'Assembly is not based on a standard assembly'}), 400
    
    try:
        # Get the current active version of the standard assembly
        from app.models import StandardAssembly, StandardAssemblyComponent
        active_standard = StandardAssembly.query.filter_by(
            base_assembly_id=assembly.standard_assembly_id,
            is_active=True,
            is_template=True
        ).first()
        
        if not active_standard:
            # Check if the original assembly is still active
            active_standard = StandardAssembly.query.filter_by(
                standard_assembly_id=assembly.standard_assembly_id,
                is_active=True,
                is_template=True
            ).first()
        
        if not active_standard:
            return jsonify({'success': False, 'error': 'No active version found for this standard assembly'}), 400
        
        # Store existing quantities before updating
        existing_quantities = {}
        for assembly_part in assembly.assembly_parts:
            existing_quantities[assembly_part.part_id] = float(assembly_part.quantity)
        
        # Delete existing assembly parts
        for assembly_part in assembly.assembly_parts:
            db.session.delete(assembly_part)
        
        # Copy components from active version
        active_components = StandardAssemblyComponent.query.filter_by(
            standard_assembly_id=active_standard.standard_assembly_id
        ).order_by(StandardAssemblyComponent.sort_order).all()
        
        for std_component in active_components:
            # Use existing quantity if part was already in assembly, otherwise use standard quantity * assembly quantity
            if std_component.part_id in existing_quantities:
                quantity_to_use = existing_quantities[std_component.part_id]
            else:
                quantity_to_use = float(std_component.quantity) * float(assembly.quantity or 1.0)
            
            new_assembly_part = AssemblyPart(
                assembly_id=assembly.assembly_id,
                part_id=std_component.part_id,
                quantity=quantity_to_use,
                unit_of_measure=std_component.unit_of_measure,
                sort_order=std_component.sort_order,
                notes=std_component.notes
            )
            db.session.add(new_assembly_part)
        
        # Update assembly version reference
        assembly.standard_assembly_version = active_standard.version
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Assembly refreshed to active version {active_standard.version}',
            'new_version': active_standard.version
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:assembly_id>/change-version', methods=['POST'])
@csrf.exempt
def change_assembly_version(assembly_id):
    """Change assembly to a specific version"""
    assembly = Assembly.query.get_or_404(assembly_id)
    
    if not assembly.standard_assembly_id:
        return jsonify({'success': False, 'error': 'Assembly is not based on a standard assembly'}), 400
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400
    
    new_version = request.json.get('version')
    if not new_version:
        return jsonify({'success': False, 'error': 'Version is required'}), 400
    
    try:
        # Find the standard assembly with the requested version
        from app.models import StandardAssembly, StandardAssemblyComponent
        
        # First check if it's the base assembly
        target_standard = StandardAssembly.query.filter_by(
            standard_assembly_id=assembly.standard_assembly_id,
            version=new_version
        ).first()
        
        # If not found, check derived versions
        if not target_standard:
            target_standard = StandardAssembly.query.filter_by(
                base_assembly_id=assembly.standard_assembly_id,
                version=new_version
            ).first()
        
        if not target_standard:
            return jsonify({'success': False, 'error': f'Version {new_version} not found'}), 404
        
        # Store existing quantities before updating
        existing_quantities = {}
        for assembly_part in assembly.assembly_parts:
            existing_quantities[assembly_part.part_id] = float(assembly_part.quantity)
        
        # Delete existing assembly parts
        for assembly_part in assembly.assembly_parts:
            db.session.delete(assembly_part)
        
        # Copy components from target version
        target_components = StandardAssemblyComponent.query.filter_by(
            standard_assembly_id=target_standard.standard_assembly_id
        ).order_by(StandardAssemblyComponent.sort_order).all()
        
        for std_component in target_components:
            # Use existing quantity if part was already in assembly, otherwise use standard quantity * assembly quantity
            if std_component.part_id in existing_quantities:
                quantity_to_use = existing_quantities[std_component.part_id]
            else:
                quantity_to_use = float(std_component.quantity) * float(assembly.quantity or 1.0)
            
            new_assembly_part = AssemblyPart(
                assembly_id=assembly.assembly_id,
                part_id=std_component.part_id,
                quantity=quantity_to_use,
                unit_of_measure=std_component.unit_of_measure,
                sort_order=std_component.sort_order,
                notes=std_component.notes
            )
            db.session.add(new_assembly_part)
        
        # Update assembly version reference
        assembly.standard_assembly_version = new_version
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Assembly changed to version {new_version}',
            'new_version': new_version
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
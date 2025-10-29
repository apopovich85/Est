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
    if new_quantity is None or new_quantity < 0:
        return jsonify({'success': False, 'error': 'Quantity must be at least 0'}), 400
    
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

        if new_quantity == 0:
            assembly.assembly_name = f"{base_name} (x0)"
        elif new_quantity > 1:
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
        
        # Delete existing assembly parts
        for assembly_part in assembly.assembly_parts:
            db.session.delete(assembly_part)
        
        # Copy components from active version
        active_components = StandardAssemblyComponent.query.filter_by(
            standard_assembly_id=active_standard.standard_assembly_id
        ).order_by(StandardAssemblyComponent.sort_order).all()
        
        for std_component in active_components:
            # Always recalculate quantity based on standard quantity * assembly quantity
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

        # Get the current standard assembly to find the base
        current_standard = StandardAssembly.query.get(assembly.standard_assembly_id)
        if not current_standard:
            print(f"ERROR: Current standard assembly not found for ID {assembly.standard_assembly_id}")
            return jsonify({'success': False, 'error': 'Current standard assembly not found'}), 404

        # Determine the base assembly ID (either the current one or its base)
        base_id = current_standard.base_assembly_id if current_standard.base_assembly_id else current_standard.standard_assembly_id
        print(f"Looking for version {new_version} in base assembly {base_id} (current: {current_standard.version})")

        # Now search for the target version:
        # 1. Check if it's the base assembly with this version
        target_standard = StandardAssembly.query.filter_by(
            standard_assembly_id=base_id,
            version=new_version
        ).first()

        # 2. If not found, check derived versions
        if not target_standard:
            target_standard = StandardAssembly.query.filter_by(
                base_assembly_id=base_id,
                version=new_version
            ).first()

        if not target_standard:
            # Log available versions for debugging
            all_versions = StandardAssembly.query.filter(
                (StandardAssembly.standard_assembly_id == base_id) |
                (StandardAssembly.base_assembly_id == base_id)
            ).all()
            available = [v.version for v in all_versions]
            print(f"ERROR: Version {new_version} not found. Available versions: {available}")
            return jsonify({
                'success': False,
                'error': f'Version {new_version} not found. Available: {", ".join(available)}'
            }), 404
        
        # Delete existing assembly parts
        for assembly_part in assembly.assembly_parts:
            db.session.delete(assembly_part)
        
        # Copy components from target version
        target_components = StandardAssemblyComponent.query.filter_by(
            standard_assembly_id=target_standard.standard_assembly_id
        ).order_by(StandardAssemblyComponent.sort_order).all()
        
        for std_component in target_components:
            # Always recalculate quantity based on standard quantity * assembly quantity
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
        
        # Update assembly version reference (both the ID and version string)
        assembly.standard_assembly_id = target_standard.standard_assembly_id
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

@bp.route('/<int:assembly_id>/copy', methods=['POST'])
@csrf.exempt
def copy_assembly(assembly_id):
    """Copy an assembly to another estimate"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        target_estimate_id = data.get('target_estimate_id')
        assembly_name = data.get('assembly_name', '').strip()
        copy_components = data.get('copy_components', True)
        
        if not target_estimate_id or not assembly_name:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Get source assembly
        source_assembly = Assembly.query.get_or_404(assembly_id)
        
        # Verify target estimate exists
        target_estimate = Estimate.query.get(target_estimate_id)
        if not target_estimate:
            return jsonify({'success': False, 'error': 'Target estimate not found'}), 404
        
        # Get the highest sort order for target estimate
        max_sort = db.session.query(db.func.max(Assembly.sort_order))\
            .filter_by(estimate_id=target_estimate_id).scalar() or 0
        
        # Create new assembly
        new_assembly = Assembly(
            estimate_id=target_estimate_id,
            assembly_name=assembly_name,
            description=source_assembly.description,
            sort_order=max_sort + 1,
            standard_assembly_id=source_assembly.standard_assembly_id,
            standard_assembly_version=source_assembly.standard_assembly_version,
            quantity=source_assembly.quantity or 1
        )
        
        db.session.add(new_assembly)
        db.session.flush()  # Get the new assembly ID
        
        components_copied = 0
        
        # Copy assembly parts if requested
        if copy_components and source_assembly.assembly_parts:
            for source_part in source_assembly.assembly_parts:
                new_part = AssemblyPart(
                    assembly_id=new_assembly.assembly_id,
                    part_id=source_part.part_id,
                    quantity=source_part.quantity,
                    unit_of_measure=source_part.unit_of_measure,
                    sort_order=source_part.sort_order,
                    notes=source_part.notes
                )
                db.session.add(new_part)
                components_copied += 1
        
        db.session.commit()
        
        message = f'Assembly copied successfully!'
        if copy_components:
            message += f' {components_copied} components copied.'
        
        return jsonify({
            'success': True,
            'message': message,
            'new_assembly_id': new_assembly.assembly_id,
            'components_copied': components_copied
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
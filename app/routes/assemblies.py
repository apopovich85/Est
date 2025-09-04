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
        
        # Calculate the quantity multiplier
        multiplier = new_quantity / old_quantity
        
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
        
        # Update all component quantities proportionally
        for component in assembly.assembly_parts:
            component.quantity = float(component.quantity) * multiplier
        
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
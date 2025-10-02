from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate, Assembly, Component, PriceHistory, EstimateComponent, Parts, StandardAssembly, StandardAssemblyComponent, AssemblyPart, EstimateRevision
from app import db, csrf
from datetime import datetime, date
import uuid
import sqlite3

bp = Blueprint('estimates', __name__)

@bp.route('/<int:estimate_id>')
def detail_estimate(estimate_id):
    """Show estimate details with breakdown"""
    estimate = Estimate.query.get_or_404(estimate_id)
    assemblies = Assembly.query.filter_by(estimate_id=estimate_id).order_by(Assembly.sort_order).all()
    individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).order_by(EstimateComponent.sort_order).all()
    
    # Calculate totals
    for assembly in assemblies:
        assembly.components = Component.query.filter_by(assembly_id=assembly.assembly_id).order_by(Component.sort_order).all()
    
    return render_template('estimates/detail.html', 
                         estimate=estimate, 
                         assemblies=assemblies,
                         individual_components=individual_components)

@bp.route('/create/<int:project_id>', methods=['GET', 'POST'])
def create_estimate(project_id):
    """Create a new estimate for a project"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            # Generate unique estimate number
            estimate_number = f"EST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Get current labor rates
            conn = sqlite3.connect('estimates.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT engineering_rate, panel_shop_rate, machine_assembly_rate
                FROM labor_rates 
                WHERE is_current = 1 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            rates = cursor.fetchone()
            conn.close()
            
            # Use current rates or fallback to defaults
            if rates:
                eng_rate, panel_rate, machine_rate = rates
            else:
                eng_rate, panel_rate, machine_rate = 145.00, 125.00, 125.00
            
            estimate = Estimate(
                project_id=project_id,
                estimate_number=estimate_number,
                estimate_name=request.form['estimate_name'],
                description=request.form.get('description', ''),
                engineering_rate=eng_rate,
                panel_shop_rate=panel_rate,
                machine_assembly_rate=machine_rate,
                rate_snapshot_date=date.today()
            )
            
            db.session.add(estimate)
            db.session.commit()
            
            flash(f'Estimate "{estimate.estimate_name}" created successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=estimate.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating estimate: {str(e)}', 'error')
    
    return render_template('estimates/create.html', project=project)

@bp.route('/<int:estimate_id>/copy', methods=['GET', 'POST'])
def copy_estimate(estimate_id):
    """Copy an existing estimate to a new project"""
    source_estimate = Estimate.query.get_or_404(estimate_id)
    projects = Project.query.all()
    
    if request.method == 'POST':
        try:
            target_project_id = request.form['target_project_id']
            
            # Create new estimate with same rates
            new_estimate_number = f"EST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            new_estimate = Estimate(
                project_id=target_project_id,
                estimate_number=new_estimate_number,
                estimate_name=f"Copy of {source_estimate.estimate_name}",
                description=source_estimate.description,
                engineering_rate=source_estimate.engineering_rate,
                panel_shop_rate=source_estimate.panel_shop_rate,
                machine_assembly_rate=source_estimate.machine_assembly_rate,
                engineering_hours=getattr(source_estimate, 'engineering_hours', 0.0),
                panel_shop_hours=getattr(source_estimate, 'panel_shop_hours', 0.0),
                machine_assembly_hours=getattr(source_estimate, 'machine_assembly_hours', 0.0)
            )
            db.session.add(new_estimate)
            db.session.flush()  # Get the new estimate ID
            
            # Copy all assemblies and assembly parts
            for assembly in source_estimate.assemblies:
                new_assembly = Assembly(
                    estimate_id=new_estimate.estimate_id,
                    assembly_name=assembly.assembly_name,
                    description=assembly.description,
                    sort_order=assembly.sort_order,
                    standard_assembly_id=assembly.standard_assembly_id,
                    standard_assembly_version=assembly.standard_assembly_version,
                    quantity=assembly.quantity
                )
                db.session.add(new_assembly)
                db.session.flush()  # Get the new assembly ID
                
                # Copy assembly parts
                for assembly_part in assembly.assembly_parts:
                    new_assembly_part = AssemblyPart(
                        assembly_id=new_assembly.assembly_id,
                        part_id=assembly_part.part_id,
                        quantity=assembly_part.quantity,
                        unit_of_measure=assembly_part.unit_of_measure,
                        sort_order=assembly_part.sort_order,
                        notes=assembly_part.notes
                    )
                    db.session.add(new_assembly_part)
            
            # Copy individual components (EstimateComponents)
            for individual_component in source_estimate.individual_components:
                new_individual_component = EstimateComponent(
                    estimate_id=new_estimate.estimate_id,
                    component_name=individual_component.component_name,
                    part_number=individual_component.part_number,
                    manufacturer=individual_component.manufacturer,
                    description=individual_component.description,
                    unit_price=individual_component.unit_price,
                    quantity=individual_component.quantity,
                    unit_of_measure=individual_component.unit_of_measure,
                    sort_order=individual_component.sort_order
                )
                db.session.add(new_individual_component)
            
            db.session.commit()
            flash('Estimate copied successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=new_estimate.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error copying estimate: {str(e)}', 'error')
    
    return render_template('estimates/copy.html', estimate=source_estimate, projects=projects)

@bp.route('/<int:estimate_id>/add-component', methods=['GET', 'POST'])
def add_individual_component(estimate_id):
    """Add individual component(s) directly to an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    if request.method == 'POST':
        try:
            # Check if this is a multiple component submission
            is_multiple = request.form.get('multiple') == 'true'
            
            if is_multiple:
                # Handle multiple components
                components_data = {}
                added_count = 0
                
                # Parse form data for multiple components
                for key, value in request.form.items():
                    if key.startswith('components[') and value.strip():
                        # Parse key like "components[1][component_name]"
                        parts = key.split('[')
                        if len(parts) >= 3:
                            row_id = parts[1].rstrip(']')
                            field_name = parts[2].rstrip(']')
                            
                            if row_id not in components_data:
                                components_data[row_id] = {}
                            components_data[row_id][field_name] = value
                
                # Create components from parsed data
                for row_id, component_data in components_data.items():
                    # Skip incomplete rows
                    if not component_data.get('component_name') or not component_data.get('unit_price'):
                        continue
                    
                    try:
                        component = EstimateComponent(
                            estimate_id=estimate_id,
                            part_id=None,  # No individual part linking for bulk add
                            component_name=component_data['component_name'],
                            description=component_data.get('description', ''),
                            part_number=component_data.get('part_number', ''),
                            manufacturer=component_data.get('manufacturer', ''),
                            unit_price=float(component_data['unit_price']),
                            quantity=float(component_data.get('quantity', 1.000)),
                            unit_of_measure=component_data.get('unit_of_measure', 'EA'),
                            category=component_data.get('category', ''),
                            notes=component_data.get('notes', ''),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        db.session.add(component)
                        added_count += 1
                    except (ValueError, KeyError) as e:
                        continue  # Skip invalid rows
                
                db.session.commit()
                flash(f'{added_count} component{"s" if added_count != 1 else ""} added successfully!', 'success')
                
            else:
                # Handle single component (legacy support)
                part_id = request.form.get('part_id') if request.form.get('part_id') else None
                
                component = EstimateComponent(
                    estimate_id=estimate_id,
                    part_id=part_id,
                    component_name=request.form['component_name'],
                    description=request.form.get('description', ''),
                    part_number=request.form.get('part_number', ''),
                    manufacturer=request.form.get('manufacturer', ''),
                    unit_price=float(request.form['unit_price']),
                    quantity=float(request.form.get('quantity', 1.000)),
                    unit_of_measure=request.form.get('unit_of_measure', 'EA'),
                    category=request.form.get('category', ''),
                    notes=request.form.get('notes', ''),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(component)
                db.session.commit()
                flash(f'Component "{component.component_name}" added successfully!', 'success')
            
            return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding component(s): {str(e)}', 'error')
    
    # Get part categories for the dropdown
    from app.models import PartCategory
    part_categories = db.session.query(PartCategory.name).filter(PartCategory.name != '').distinct().all()
    part_categories = [cat[0] for cat in part_categories if cat[0]]
    
    return render_template('estimates/add_component.html', 
                         estimate=estimate, 
                         part_categories=part_categories)

@bp.route('/component/<int:component_id>/edit', methods=['GET', 'POST'])
def edit_individual_component(component_id):
    """Edit an individual estimate component"""
    component = EstimateComponent.query.get_or_404(component_id)
    estimate = component.estimate
    
    if request.method == 'POST':
        try:
            component.component_name = request.form['component_name']
            component.description = request.form.get('description', '')
            component.part_number = request.form.get('part_number', '')
            component.manufacturer = request.form.get('manufacturer', '')
            component.unit_price = float(request.form['unit_price'])
            component.quantity = float(request.form.get('quantity', 1.000))
            component.unit_of_measure = request.form.get('unit_of_measure', 'EA')
            component.category = request.form.get('category', '')
            component.notes = request.form.get('notes', '')
            component.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Component "{component.component_name}" updated successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=estimate.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating component: {str(e)}', 'error')
    
    # Get part categories for the dropdown
    from app.models import PartCategory
    part_categories = db.session.query(PartCategory.name).filter(PartCategory.name != '').distinct().all()
    part_categories = [cat[0] for cat in part_categories if cat[0]]
    
    return render_template('estimates/edit_component.html', 
                         estimate=estimate, 
                         component=component, 
                         part_categories=part_categories)

@bp.route('/component/<int:component_id>/delete', methods=['POST'])
@csrf.exempt
def delete_individual_component(component_id):
    """Delete an individual estimate component"""
    component = EstimateComponent.query.get_or_404(component_id)
    estimate_id = component.estimate_id
    component_name = component.component_name
    
    try:
        db.session.delete(component)
        db.session.commit()
        flash(f'Component "{component_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting component: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))





def _get_bom_data_for_estimate(estimate_id):
    """Helper function to get BOM data for an estimate - used by both web and PDF endpoints"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    # Get all components from assemblies and individual components
    bom_data = []
    
    # Get components from assemblies
    assemblies = Assembly.query.filter_by(estimate_id=estimate_id).all()
    for assembly in assemblies:
        for assembly_part in assembly.assembly_parts:
            # Get part details through relationship
            part = assembly_part.part
            if not part:
                continue  # Skip if no part relationship
            
            # Use the assembly part quantity directly (already accounts for assembly multiplier)
            total_quantity = assembly_part.quantity
            
            # Create a unique grouping key for this specific part
            # Use part_id as the primary key to avoid confusion between different parts
            grouping_key = f"part_{part.part_id}"
            display_part_number = part.master_item_number or part.part_number or "N/A"
            
            # Check if this exact part already exists in BOM
            existing_item = next((item for item in bom_data 
                                if item['grouping_key'] == grouping_key), None)
            
            if existing_item:
                # Add to existing quantity
                existing_item['total_quantity'] += float(total_quantity)
            else:
                # Add new item
                bom_data.append({
                    'grouping_key': grouping_key,  # Internal key for grouping
                    'part_number': display_part_number,
                    'component_name': part.description or part.model or 'Component',
                    'description': part.description,
                    'manufacturer': part.manufacturer,
                    'unit_price': float(part.current_price or 0.0),
                    'unit_of_measure': assembly_part.unit_of_measure,
                    'total_quantity': float(total_quantity),
                    'category': part.category
                })
    
    # Get individual components
    individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).all()
    for component in individual_components:
        # For individual components, use the component ID as grouping key
        if component.part:
            grouping_key = f"part_{component.part.part_id}"
            display_part_number = component.part.master_item_number or component.part.part_number or "N/A"
            manufacturer = component.part.manufacturer
            category = component.part.category
        else:
            grouping_key = f"component_{component.estimate_component_id}"
            display_part_number = component.part_number or "N/A"
            manufacturer = component.manufacturer
            category = component.category or 'Uncategorized'
        
        # Check if this exact part already exists in BOM
        existing_item = next((item for item in bom_data 
                            if item['grouping_key'] == grouping_key), None)
        
        if existing_item:
            # Add to existing quantity
            existing_item['total_quantity'] += float(component.quantity)
        else:
            # Add new item
            bom_data.append({
                'grouping_key': grouping_key,  # Internal key for grouping
                'part_number': display_part_number,
                'component_name': component.component_name,
                'description': component.description,
                'manufacturer': manufacturer or 'N/A',
                'unit_price': float(component.unit_price),
                'unit_of_measure': component.unit_of_measure,
                'total_quantity': float(component.quantity),
                'category': category
            })
    
    # Remove the grouping_key from the final output and sort by part number
    for item in bom_data:
        item.pop('grouping_key', None)
        
    bom_data.sort(key=lambda x: x['part_number'] or '')
    
    return estimate, bom_data


@bp.route('/<int:estimate_id>/bom')
def get_bom_data(estimate_id):
    """Get Bill of Materials data for an estimate"""
    try:
        # Use the helper function to get BOM data
        estimate, bom_data = _get_bom_data_for_estimate(estimate_id)
        
        return jsonify({
            'success': True,
            'bom': bom_data,
            'estimate': {
                'name': estimate.estimate_name,
                'number': estimate.estimate_number,
                'project': estimate.project.project_name
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/<int:estimate_id>/bom/pdf', methods=['POST'])
@csrf.exempt
def export_bom_pdf(estimate_id):
    """Export Bill of Materials as PDF using the pdf_reports module"""
    from flask import make_response
    from app.pdf_reports import generate_bom_pdf, get_bom_filename
    
    try:
        # Use the helper function to get BOM data (same logic as web endpoint)
        estimate, bom_data = _get_bom_data_for_estimate(estimate_id)
        
        # Generate PDF using the pdf_reports module
        pdf_buffer = generate_bom_pdf(estimate, bom_data)
        
        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={get_bom_filename(estimate)}'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'PDF generation failed: {str(e)}'
        }), 500


@bp.route('/<int:estimate_id>/update-labor-hours', methods=['POST'])
@csrf.exempt
def update_labor_hours(estimate_id):
    """Update labor hours for an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        engineering_hours = request.form.get('engineering_hours', 0)
        panel_shop_hours = request.form.get('panel_shop_hours', 0)
        machine_assembly_hours = request.form.get('machine_assembly_hours', 0)
        
        estimate.engineering_hours = float(engineering_hours or 0)
        estimate.panel_shop_hours = float(panel_shop_hours or 0)
        estimate.machine_assembly_hours = float(machine_assembly_hours or 0)
        estimate.updated_at = datetime.now()
        
        db.session.commit()
        flash('Labor hours updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating labor hours: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))

@bp.route('/<int:estimate_id>/update-name', methods=['POST'])
@csrf.exempt
def update_estimate_name(estimate_id):
    """Update estimate name via AJAX"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        data = request.get_json()
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'error': 'Estimate name cannot be empty'}), 400
        
        if len(new_name) > 255:
            return jsonify({'success': False, 'error': 'Estimate name too long (maximum 255 characters)'}), 400
        
        estimate.estimate_name = new_name
        estimate.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True, 'name': new_name})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:estimate_id>/totals', methods=['GET'])
def get_estimate_totals(estimate_id):
    """API endpoint to get updated estimate totals"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        # Format currency values
        def format_currency(amount):
            return f"${amount:,.2f}"
        
        return jsonify({
            'success': True,
            'totals': {
                'grand_total': format_currency(estimate.grand_total),
                'materials_total': format_currency(estimate.calculated_total), 
                'labor_total': format_currency(estimate.total_labor_cost),
                'raw_grand_total': float(estimate.grand_total),
                'raw_materials_total': float(estimate.calculated_total),
                'raw_labor_total': float(estimate.total_labor_cost)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<int:estimate_id>/reorder-assemblies', methods=['POST'])
@csrf.exempt
def reorder_assemblies(estimate_id):
    """Update assembly sort order via AJAX"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No updates provided'}), 400
        
        # Validate that all assemblies belong to this estimate
        assembly_ids = [update['assembly_id'] for update in updates]
        assemblies = Assembly.query.filter(
            Assembly.assembly_id.in_(assembly_ids),
            Assembly.estimate_id == estimate_id
        ).all()
        
        if len(assemblies) != len(assembly_ids):
            return jsonify({'success': False, 'error': 'Some assemblies do not belong to this estimate'}), 400
        
        # Create a map for quick lookup
        assembly_map = {assembly.assembly_id: assembly for assembly in assemblies}
        
        # Update sort orders
        for update in updates:
            assembly_id = update['assembly_id']
            new_sort_order = update['sort_order']
            
            if assembly_id in assembly_map:
                assembly_map[assembly_id].sort_order = new_sort_order
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Assembly order updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:estimate_id>/bulk-delete-components', methods=['POST'])
@csrf.exempt
def bulk_delete_components(estimate_id):
    """Delete multiple individual components via AJAX"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        data = request.get_json()
        component_ids = data.get('component_ids', [])
        
        if not component_ids:
            return jsonify({'success': False, 'error': 'No components specified for deletion'}), 400
        
        if not isinstance(component_ids, list):
            return jsonify({'success': False, 'error': 'component_ids must be a list'}), 400
        
        # Validate that all components belong to this estimate and exist
        components = EstimateComponent.query.filter(
            EstimateComponent.estimate_component_id.in_(component_ids),
            EstimateComponent.estimate_id == estimate_id
        ).all()
        
        if len(components) != len(component_ids):
            return jsonify({'success': False, 'error': 'Some components do not belong to this estimate or do not exist'}), 400
        
        # Delete the components
        deleted_count = 0
        for component in components:
            db.session.delete(component)
            deleted_count += 1
        
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {deleted_count} component{"s" if deleted_count != 1 else ""}',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/individual-components/<int:component_id>/update-quantity', methods=['POST'])
@csrf.exempt
def update_individual_component_quantity(component_id):
    """Update individual component quantity via AJAX"""
    component = EstimateComponent.query.get_or_404(component_id)
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400
    
    new_quantity = request.json.get('quantity')
    if new_quantity is None:
        return jsonify({'success': False, 'error': 'Quantity is required'}), 400
    
    try:
        new_quantity = float(new_quantity)
        if new_quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be greater than 0'}), 400
        
        old_quantity = float(component.quantity)
        component.quantity = new_quantity
        component.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Individual component quantity updated from {old_quantity} to {new_quantity}',
            'old_quantity': old_quantity,
            'new_quantity': new_quantity,
            'new_total': float(new_quantity) * float(component.unit_price)
        })
        
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid quantity format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:estimate_id>/delete', methods=['POST'])
@csrf.exempt
def delete_estimate(estimate_id):
    """Delete an estimate and all its associated components"""
    estimate = Estimate.query.get_or_404(estimate_id)
    project_id = estimate.project_id
    estimate_name = estimate.estimate_name

    try:
        db.session.delete(estimate)
        db.session.commit()
        flash(f'Estimate "{estimate_name}" deleted successfully!', 'success')
        return redirect(url_for('projects.detail_project', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting estimate: {str(e)}', 'error')
        return redirect(url_for('projects.detail_project', project_id=project_id))

@bp.route('/<int:estimate_id>/toggle-optional', methods=['POST'])
@csrf.exempt
def toggle_optional(estimate_id):
    """Toggle estimate between optional and standard"""
    estimate = Estimate.query.get_or_404(estimate_id)

    try:
        estimate.is_optional = not estimate.is_optional
        estimate.updated_at = datetime.utcnow()
        db.session.commit()

        status = "optional" if estimate.is_optional else "standard"
        return jsonify({
            'success': True,
            'is_optional': estimate.is_optional,
            'message': f'Estimate marked as {status}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating estimate: {str(e)}'
        }), 500

@bp.route('/api/reorder', methods=['POST'])
@csrf.exempt
def reorder_estimates():
    """API endpoint to reorder estimates within a project"""
    try:
        data = request.get_json()
        if not data or 'estimate_ids' not in data:
            return jsonify({'success': False, 'error': 'Missing estimate_ids'}), 400
        
        estimate_ids = data['estimate_ids']
        
        # Update sort_order for each estimate
        for index, estimate_id in enumerate(estimate_ids):
            estimate = Estimate.query.get(estimate_id)
            if estimate:
                estimate.sort_order = index
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Estimates reordered successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/list', methods=['GET'])
def list_estimates_api():
    """API endpoint to get list of all estimates for copying assemblies"""
    try:
        estimates = db.session.query(
            Estimate.estimate_id,
            Estimate.estimate_name,
            Project.project_name
        ).join(Project).order_by(Project.project_name, Estimate.estimate_name).all()
        
        estimate_list = []
        for estimate in estimates:
            estimate_list.append({
                'estimate_id': estimate.estimate_id,
                'estimate_name': estimate.estimate_name,
                'project_name': estimate.project_name
            })
        
        return jsonify({'success': True, 'estimates': estimate_list})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:estimate_id>/create-revision', methods=['POST'])
@csrf.exempt
def create_revision(estimate_id):
    """Create a new revision of an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        changes_summary = request.form.get('changes_summary', '').strip()
        detailed_changes = request.form.get('detailed_changes', '').strip()
        created_by = request.form.get('created_by', 'System').strip()
        
        if not changes_summary:
            flash('Changes summary is required to create a revision', 'error')
            return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))
        
        # Create the revision
        revision = estimate.create_revision(
            changes_summary=changes_summary,
            detailed_changes=detailed_changes,
            created_by=created_by
        )
        
        db.session.commit()
        flash(f'Revision {estimate.revision_number} created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating revision: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))

@bp.route('/<int:estimate_id>/revision-history')
def revision_history(estimate_id):
    """View revision history for an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    revisions = estimate.get_revision_history()
    
    return render_template('estimates/revision_history.html', 
                         estimate=estimate, 
                         revisions=revisions)

@bp.route('/<int:estimate_id>/revision-report/pdf')
def export_revision_report_pdf(estimate_id):
    """Export revision history report as PDF"""
    from flask import make_response
    from app.pdf_reports import generate_revision_report_pdf
    
    try:
        estimate = Estimate.query.get_or_404(estimate_id)
        revisions = estimate.get_revision_history()
        
        # Generate PDF
        pdf_buffer = generate_revision_report_pdf(estimate, revisions)
        
        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="revision_history_{estimate.estimate_number}.pdf"'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'PDF generation failed: {str(e)}'
        }), 500
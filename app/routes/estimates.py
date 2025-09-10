from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate, Assembly, Component, PriceHistory, EstimateComponent, Parts, StandardAssembly, StandardAssemblyComponent, AssemblyPart
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
                machine_assembly_rate=source_estimate.machine_assembly_rate
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
                    quantity=assembly.quantity,
                    engineering_hours=assembly.engineering_hours,
                    panel_shop_hours=assembly.panel_shop_hours,
                    machine_assembly_hours=assembly.machine_assembly_hours,
                    estimated_by=assembly.estimated_by,
                    time_estimate_notes=assembly.time_estimate_notes
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
                    sort_order=individual_component.sort_order,
                    engineering_hours=individual_component.engineering_hours,
                    panel_shop_hours=individual_component.panel_shop_hours,
                    machine_assembly_hours=individual_component.machine_assembly_hours,
                    estimated_by=individual_component.estimated_by,
                    time_estimate_notes=individual_component.time_estimate_notes
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
    """Add an individual component directly to an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    if request.method == 'POST':
        try:
            part_id = request.form.get('part_id') if request.form.get('part_id') else None
            part = Parts.query.get(part_id) if part_id else None
            
            # Create new individual component
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
            flash(f'Error adding component: {str(e)}', 'error')
    
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



@bp.route('/<int:estimate_id>/manage-component-hours')
def manage_component_hours(estimate_id):
    """Manage time estimates for all individual components in an estimate"""
    estimate = Estimate.query.get_or_404(estimate_id)
    components = EstimateComponent.query.filter_by(estimate_id=estimate_id).order_by(EstimateComponent.sort_order).all()
    
    return render_template('estimates/manage_component_hours.html', estimate=estimate, components=components)


@bp.route('/<int:estimate_id>/update-component-hours', methods=['POST'])
@csrf.exempt
def update_component_hours(estimate_id):
    """Update time estimates for multiple individual components"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        # Process each component's time data
        for component in estimate.individual_components:
            component_id = component.estimate_component_id
            
            # Get form data for this component
            engineering_hours = request.form.get(f'engineering_hours_{component_id}', 0)
            panel_shop_hours = request.form.get(f'panel_shop_hours_{component_id}', 0)
            machine_assembly_hours = request.form.get(f'machine_assembly_hours_{component_id}', 0)
            estimated_by = request.form.get(f'estimated_by_{component_id}', '')
            time_estimate_notes = request.form.get(f'time_estimate_notes_{component_id}', '')
            
            # Update component with new values
            component.engineering_hours = float(engineering_hours or 0)
            component.panel_shop_hours = float(panel_shop_hours or 0)
            component.machine_assembly_hours = float(machine_assembly_hours or 0)
            component.estimated_by = estimated_by
            component.time_estimate_notes = time_estimate_notes
        
        db.session.commit()
        flash('Component time estimates updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating component time estimates: {str(e)}', 'error')
    
    return redirect(url_for('estimates.detail_estimate', estimate_id=estimate_id))


@bp.route('/<int:estimate_id>/bom')
def get_bom_data(estimate_id):
    """Get Bill of Materials data for an estimate"""
    try:
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
                
                # Check if this part already exists in BOM
                existing_item = next((item for item in bom_data 
                                    if item['part_number'] == part.part_number), None)
                
                if existing_item:
                    # Add to existing quantity
                    existing_item['total_quantity'] += float(total_quantity)
                else:
                    # Add new item
                    bom_data.append({
                        'part_number': part.part_number,
                        'component_name': part.description or part.model or 'Component',
                        'description': part.description,
                        'manufacturer': part.manufacturer,
                        'unit_price': float(part.current_price or 0.0),
                        'unit_of_measure': assembly_part.unit_of_measure,
                        'total_quantity': float(total_quantity),
                        'category': part.category  # Get the actual category from the part
                    })
        
        # Get individual components
        individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).all()
        for component in individual_components:
            # Check if this part already exists in BOM
            existing_item = next((item for item in bom_data 
                                if item['part_number'] == component.part_number), None)
            
            if existing_item:
                # Add to existing quantity
                existing_item['total_quantity'] += float(component.quantity)
            else:
                # Add new item
                bom_data.append({
                    'part_number': component.part_number,
                    'component_name': component.component_name,
                    'description': component.description,
                    'manufacturer': component.manufacturer or 'N/A',  # Use manufacturer if available
                    'unit_price': float(component.unit_price),
                    'unit_of_measure': component.unit_of_measure,
                    'total_quantity': float(component.quantity),
                    'category': component.category or 'Uncategorized'  # Use category from component
                })
        
        # Sort by part number
        bom_data.sort(key=lambda x: x['part_number'] or '')
        
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
        # Get estimate and BOM data
        estimate = Estimate.query.get_or_404(estimate_id)
        
        # Get BOM data using the same logic as get_bom_data
        bom_data = []
        assemblies = Assembly.query.filter_by(estimate_id=estimate_id).all()
        
        for assembly in assemblies:
            for assembly_part in assembly.assembly_parts:
                # Get part details through relationship
                part = assembly_part.part
                if not part:
                    continue  # Skip if no part relationship
                
                # Use the assembly part quantity directly (already accounts for assembly multiplier)
                total_quantity = assembly_part.quantity
                
                # Check if this part already exists in BOM
                existing_item = next((item for item in bom_data 
                                    if item['part_number'] == part.part_number), None)
                
                if existing_item:
                    # Add to existing quantity
                    existing_item['total_quantity'] += float(total_quantity)
                else:
                    # Add new item
                    bom_data.append({
                        'part_number': part.part_number,
                        'component_name': part.description or part.model or 'Component',
                        'description': part.description,
                        'manufacturer': part.manufacturer,
                        'unit_price': float(part.current_price or 0.0),
                        'unit_of_measure': assembly_part.unit_of_measure,
                        'total_quantity': float(total_quantity),
                        'category': part.category  # Get the actual category from the part
                    })
        
        individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).all()
        for component in individual_components:
            existing_item = next((item for item in bom_data 
                                if item['part_number'] == component.part_number), None)
            
            if existing_item:
                existing_item['total_quantity'] += float(component.quantity)
            else:
                bom_data.append({
                    'part_number': component.part_number,
                    'component_name': component.component_name,
                    'description': component.description,
                    'manufacturer': component.manufacturer or 'N/A',  # Use manufacturer if available
                    'unit_price': float(component.unit_price),
                    'unit_of_measure': component.unit_of_measure,
                    'total_quantity': float(component.quantity),
                    'category': component.category or 'Uncategorized'  # Use category from component
                })
        
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

@bp.route('/<int:estimate_id>/manage-all-hours')
def manage_all_hours(estimate_id):
    """Manage time estimates for both assemblies and individual components in one unified interface"""
    estimate = Estimate.query.get_or_404(estimate_id)
    assemblies = Assembly.query.filter_by(estimate_id=estimate_id).order_by(Assembly.sort_order).all()
    individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).order_by(EstimateComponent.sort_order).all()
    
    return render_template('estimates/manage_all_hours.html', 
                         estimate=estimate, 
                         assemblies=assemblies,
                         individual_components=individual_components)

@bp.route('/<int:estimate_id>/update-all-hours', methods=['POST'])
@csrf.exempt
def update_all_hours(estimate_id):
    """Update time estimates for both assemblies and individual components"""
    estimate = Estimate.query.get_or_404(estimate_id)
    
    try:
        # Process assembly hours
        for assembly in estimate.assemblies:
            assembly_id = assembly.assembly_id
            
            # Get form data for this assembly (prefixed with "assembly_")
            engineering_hours = request.form.get(f'assembly_engineering_hours_{assembly_id}', 0)
            panel_shop_hours = request.form.get(f'assembly_panel_shop_hours_{assembly_id}', 0)
            machine_assembly_hours = request.form.get(f'assembly_machine_assembly_hours_{assembly_id}', 0)
            estimated_by = request.form.get(f'assembly_estimated_by_{assembly_id}', '')
            time_estimate_notes = request.form.get(f'assembly_time_estimate_notes_{assembly_id}', '')
            
            # Update assembly with new values
            assembly.engineering_hours = float(engineering_hours or 0)
            assembly.panel_shop_hours = float(panel_shop_hours or 0)
            assembly.machine_assembly_hours = float(machine_assembly_hours or 0)
            assembly.estimated_by = estimated_by
            assembly.time_estimate_notes = time_estimate_notes

        # Process individual component hours
        individual_components = EstimateComponent.query.filter_by(estimate_id=estimate_id).all()
        for component in individual_components:
            component_id = component.estimate_component_id
            
            # Get form data for this component (prefixed with "component_")
            engineering_hours = request.form.get(f'component_engineering_hours_{component_id}', 0)
            panel_shop_hours = request.form.get(f'component_panel_shop_hours_{component_id}', 0)
            machine_assembly_hours = request.form.get(f'component_machine_assembly_hours_{component_id}', 0)
            estimated_by = request.form.get(f'component_estimated_by_{component_id}', '')
            time_estimate_notes = request.form.get(f'component_time_estimate_notes_{component_id}', '')
            
            # Update component with new values
            component.engineering_hours = float(engineering_hours or 0)
            component.panel_shop_hours = float(panel_shop_hours or 0)
            component.machine_assembly_hours = float(machine_assembly_hours or 0)
            component.estimated_by = estimated_by
            component.time_estimate_notes = time_estimate_notes
        
        db.session.commit()
        flash('All time estimates updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating time estimates: {str(e)}', 'error')
    
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
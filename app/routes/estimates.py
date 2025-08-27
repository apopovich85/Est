from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate, Assembly, Component, PriceHistory, EstimateComponent, Parts
from app import db, csrf
from datetime import datetime
import uuid

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
            
            estimate = Estimate(
                project_id=project_id,
                estimate_number=estimate_number,
                estimate_name=request.form['estimate_name'],
                description=request.form.get('description', '')
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
            
            # Create new estimate
            new_estimate_number = f"EST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            new_estimate = Estimate(
                project_id=target_project_id,
                estimate_number=new_estimate_number,
                estimate_name=f"Copy of {source_estimate.estimate_name}",
                description=source_estimate.description
            )
            db.session.add(new_estimate)
            db.session.flush()  # Get the new estimate ID
            
            # Copy all assemblies and components
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
    part_categories = db.session.query(Parts.category).distinct().filter(Parts.category != '').all()
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
    part_categories = db.session.query(Parts.category).distinct().filter(Parts.category != '').all()
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
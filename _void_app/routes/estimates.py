from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate, Assembly, Component, PriceHistory
from app import db
from datetime import datetime
import uuid

bp = Blueprint('estimates', __name__)

@bp.route('/<int:estimate_id>')
def detail_estimate(estimate_id):
    """Show estimate details with breakdown"""
    estimate = Estimate.query.get_or_404(estimate_id)
    assemblies = Assembly.query.filter_by(estimate_id=estimate_id).order_by(Assembly.sort_order).all()
    
    # Calculate totals
    for assembly in assemblies:
        assembly.components = Component.query.filter_by(assembly_id=assembly.assembly_id).order_by(Component.sort_order).all()
    
    return render_template('estimates/detail.html', estimate=estimate, assemblies=assemblies)

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
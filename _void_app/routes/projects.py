from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate
from app import db
from datetime import datetime

bp = Blueprint('projects', __name__)

@bp.route('/')
def list_projects():
    """List all projects"""
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    return render_template('projects/list.html', projects=projects)

@bp.route('/create', methods=['GET', 'POST'])
def create_project():
    """Create a new project"""
    if request.method == 'POST':
        try:
            project = Project(
                project_name=request.form['project_name'],
                client_name=request.form['client_name'],
                description=request.form.get('description', ''),
                status=request.form.get('status', 'Draft')
            )
            
            db.session.add(project)
            db.session.commit()
            
            flash(f'Project "{project.project_name}" created successfully!', 'success')
            return redirect(url_for('projects.detail_project', project_id=project.project_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating project: {str(e)}', 'error')
    
    return render_template('projects/create.html')

@bp.route('/<int:project_id>')
def detail_project(project_id):
    """Show project details with all estimates"""
    project = Project.query.get_or_404(project_id)
    estimates = Estimate.query.filter_by(project_id=project_id).order_by(Estimate.created_at.desc()).all()
    
    return render_template('projects/detail.html', project=project, estimates=estimates)

@bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    """Edit an existing project"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            project.project_name = request.form['project_name']
            project.client_name = request.form['client_name']
            project.description = request.form.get('description', '')
            project.status = request.form.get('status', 'Draft')
            project.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Project updated successfully!', 'success')
            return redirect(url_for('projects.detail_project', project_id=project_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating project: {str(e)}', 'error')
    
    return render_template('projects/edit.html', project=project)

@bp.route('/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project"""
    project = Project.query.get_or_404(project_id)
    
    try:
        project_name = project.project_name
        db.session.delete(project)
        db.session.commit()
        flash(f'Project "{project_name}" deleted successfully!', 'success')
        return redirect(url_for('projects.list_projects'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {str(e)}', 'error')
        return redirect(url_for('projects.detail_project', project_id=project_id))

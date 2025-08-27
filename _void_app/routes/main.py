from flask import Blueprint, render_template
from app.models import Project, Estimate
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    """Dashboard showing overview of all projects"""
    projects = db.session.query(Project).order_by(Project.updated_at.desc()).all()
    
    # Calculate summary statistics
    total_projects = len(projects)
    total_estimates = db.session.query(Estimate).count()
    total_value = sum(project.total_value() for project in projects)
    
    # Get recent activity (last 5 updated projects)
    recent_projects = projects[:5]
    
    return render_template('index.html',
                         projects=projects,
                         recent_projects=recent_projects,
                         total_projects=total_projects,
                         total_estimates=total_estimates,
                         total_value=total_value)
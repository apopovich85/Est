from flask import Blueprint, render_template, request
from app.models import Project, Estimate
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    """Dashboard showing overview of all projects"""
    # Get filter parameter from query string (default to 'active')
    filter_type = request.args.get('filter', 'active')

    # Build query based on filter
    query = db.session.query(Project)
    if filter_type == 'active':
        query = query.filter(Project.is_active == True)
    elif filter_type == 'closed':
        query = query.filter(Project.is_active == False)
    # 'all' shows everything

    projects = query.order_by(Project.updated_at.desc()).all()

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
                         total_value=total_value,
                         current_filter=filter_type)
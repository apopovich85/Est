from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Assembly, Estimate
from app import db

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
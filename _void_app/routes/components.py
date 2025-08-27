from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Component, PriceHistory, Assembly
from app import db
from datetime import datetime

bp = Blueprint('components', __name__)

@bp.route('/create/<int:assembly_id>', methods=['GET', 'POST'])
def create_component(assembly_id):
    """Create a new component"""
    assembly = Assembly.query.get_or_404(assembly_id)
    
    if request.method == 'POST':
        try:
            component = Component(
                assembly_id=assembly_id,
                component_name=request.form['component_name'],
                description=request.form.get('description', ''),
                part_number=request.form.get('part_number', ''),
                unit_price=float(request.form['unit_price']),
                quantity=float(request.form['quantity']),
                unit_of_measure=request.form.get('unit_of_measure', 'EA')
            )
            
            db.session.add(component)
            db.session.commit()
            
            flash(f'Component "{component.component_name}" added successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=assembly.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating component: {str(e)}', 'error')
    
    return render_template('components/create.html', assembly=assembly)

@bp.route('/<int:component_id>/edit', methods=['GET', 'POST'])
def edit_component(component_id):
    """Edit an existing component"""
    component = Component.query.get_or_404(component_id)
    
    if request.method == 'POST':
        try:
            old_price = float(component.unit_price)
            new_price = float(request.form['unit_price'])
            
            # Update component
            component.component_name = request.form['component_name']
            component.description = request.form.get('description', '')
            component.part_number = request.form.get('part_number', '')
            component.unit_price = new_price
            component.quantity = float(request.form['quantity'])
            component.unit_of_measure = request.form.get('unit_of_measure', 'EA')
            component.updated_at = datetime.utcnow()
            
            # Track price change
            if old_price != new_price:
                price_history = PriceHistory(
                    component_id=component_id,
                    old_price=old_price,
                    new_price=new_price,
                    changed_reason='Manual price update'
                )
                db.session.add(price_history)
            
            db.session.commit()
            flash('Component updated successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=component.assembly.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating component: {str(e)}', 'error')
    
    return render_template('components/edit.html', component=component)

@bp.route('/<int:component_id>/price-history')
def price_history(component_id):
    """Show component price history with chart"""
    component = Component.query.get_or_404(component_id)
    history = PriceHistory.query.filter_by(component_id=component_id).order_by(PriceHistory.changed_at).all()
    
    return render_template('components/price_history.html', component=component, history=history)

@bp.route('/<int:component_id>/price-history-data')
def price_history_data(component_id):
    """API endpoint for price history chart data"""
    component = Component.query.get_or_404(component_id)
    history = PriceHistory.query.filter_by(component_id=component_id).order_by(PriceHistory.changed_at).all()
    
    # Prepare data for Chart.js
    chart_data = {
        'labels': [h.changed_at.strftime('%Y-%m-%d %H:%M') for h in history],
        'datasets': [{
            'label': 'Unit Price',
            'data': [float(h.new_price) for h in history],
            'borderColor': 'rgb(75, 192, 192)',
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'tension': 0.1
        }]
    }
    
    return jsonify(chart_data)
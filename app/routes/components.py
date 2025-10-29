from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from app.models import Component, PriceHistory, Assembly, Parts, Estimate, Project, PartsPriceHistory, AssemblyPart, PartCategory, EstimateComponent, StandardAssemblyComponent, TechData, Motor
from app import db, csrf
from datetime import datetime
import csv
import io
import zipfile

bp = Blueprint('components', __name__)

@bp.route('/create/<int:assembly_id>', methods=['GET', 'POST'])
@csrf.exempt
def create_component(assembly_id):
    """Add a part to an assembly"""
    assembly = Assembly.query.get_or_404(assembly_id)
    
    if request.method == 'POST':
        try:
            # Require a part_id to be provided (must select from existing catalog)
            part_id = request.form.get('part_id')
            
            if not part_id:
                flash('You must select a part from the catalog. Parts cannot be created when adding to assemblies.', 'error')
                return render_template('components/create.html', assembly=assembly)
            
            # Adding an existing part from catalog
            part = Parts.query.get_or_404(part_id)
            assembly_part = AssemblyPart(
                assembly_id=assembly_id,
                part_id=part_id,
                quantity=float(request.form.get('quantity', 1.0)),
                unit_of_measure=request.form.get('unit_of_measure', 'EA'),
                notes=request.form.get('notes', '')
            )
            
            db.session.add(assembly_part)
            db.session.commit()
            
            flash(f'Part "{part.description or part.part_number}" added to assembly successfully!', 'success')
            
            return redirect(url_for('estimates.detail_estimate', estimate_id=assembly.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding part to assembly: {str(e)}', 'error')
    
    return render_template('components/create.html', assembly=assembly)

@bp.route('/api/part/<int:part_id>')
def get_part_data(part_id):
    """API endpoint to get part data for auto-filling component form"""
    part = Parts.query.get_or_404(part_id)
    
    return jsonify({
        'part_id': part.part_id,
        'part_number': part.part_number,
        'component_name': part.description or part.part_number,
        'description': part.description,
        'unit_price': part.current_price,
        'manufacturer': part.manufacturer,
        'category': part.category,
        'model': part.model,
        'rating': part.rating
    })

@bp.route('/<int:component_id>/edit', methods=['GET', 'POST'])
def edit_component(component_id):
    """Edit an existing component (handles both Component and AssemblyPart)"""
    # Try to find in AssemblyPart first (new system)
    assembly_part = AssemblyPart.query.get(component_id)
    if assembly_part:
        return edit_assembly_part(assembly_part)
    
    # Fall back to old Component system
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

def edit_assembly_part(assembly_part):
    """Edit an AssemblyPart (new system)"""
    if request.method == 'POST':
        try:
            # Check if part was changed
            new_part_id = request.form.get('part_id', type=int)
            if new_part_id and new_part_id != assembly_part.part_id:
                # Changing to a different part
                new_part = Parts.query.get_or_404(new_part_id)
                assembly_part.part_id = new_part_id
                flash(f'Part changed to: {new_part.description or new_part.part_number}', 'info')
            
            # Update assembly part fields
            assembly_part.quantity = float(request.form['quantity'])
            assembly_part.unit_of_measure = request.form.get('unit_of_measure', 'EA')
            assembly_part.notes = request.form.get('notes', '')
            
            # Handle price update if not changing parts
            if not new_part_id or new_part_id == assembly_part.part_id:
                old_price = assembly_part.unit_price
                new_price = float(request.form['unit_price'])
                
                if old_price != new_price:
                    # Track price history for the part
                    price_history = PartsPriceHistory(
                        part_id=assembly_part.part_id,
                        old_price=old_price,
                        new_price=new_price,
                        changed_reason='Assembly component edit'
                    )
                    db.session.add(price_history)
                    
                    # Update the part price
                    assembly_part.part.update_price(
                        new_price=new_price,
                        reason='Assembly component edit',
                        source='manual'
                    )
            
            assembly_part.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Component updated successfully!', 'success')
            return redirect(url_for('estimates.detail_estimate', estimate_id=assembly_part.assembly.estimate_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating component: {str(e)}', 'error')
    
    # Get similar parts for selection (same category)
    similar_parts = []
    if assembly_part.part.category_id:
        # First try same category
        similar_parts = Parts.query.filter_by(category_id=assembly_part.part.category_id)\
            .order_by(Parts.description, Parts.part_number)\
            .all()
        
        # If only one part in category (the current one), expand to show all parts for flexibility
        if len(similar_parts) <= 1:
            similar_parts = Parts.query.order_by(Parts.category_id, Parts.description, Parts.part_number)\
                .limit(50)\
                .all()  # Show top 50 parts from all categories
    
    return render_template('components/edit_assembly_part.html', 
                         assembly_part=assembly_part,
                         similar_parts=similar_parts)

@bp.route('/<int:component_id>/price-history')
def price_history(component_id):
    """Show component price history with chart"""
    component = Component.query.get_or_404(component_id)
    history = PriceHistory.query.filter_by(component_id=component_id).order_by(PriceHistory.changed_at).all()
    
    return render_template('components/price_history.html', component=component, history=history)

@bp.route('/<int:component_id>/price-history-data')
def price_history_data(component_id):
    """Enhanced API endpoint for price history chart data with statistics"""
    component = Component.query.get_or_404(component_id)
    history = PriceHistory.query.filter_by(component_id=component_id).order_by(PriceHistory.changed_at).all()
    
    if not history:
        # If no history, create a single point with current price
        chart_data = {
            'labels': [component.created_at.strftime('%Y-%m-%d %H:%M')],
            'datasets': [{
                'label': 'Unit Price',
                'data': [float(component.unit_price)],
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                'tension': 0.1,
                'pointRadius': 4,
                'pointHoverRadius': 6
            }]
        }
        
        statistics = {
            'current_price': float(component.unit_price),
            'total_changes': 0,
            'trend': 'stable',
            'min_price': float(component.unit_price),
            'max_price': float(component.unit_price),
            'avg_price': float(component.unit_price)
        }
    else:
        # Create chart data
        labels = []
        data_points = []
        
        # Add creation point if we have history
        if history:
            labels.append(component.created_at.strftime('%Y-%m-%d %H:%M'))
            data_points.append(float(history[0].old_price) if history[0].old_price else float(component.unit_price))
        
        # Add all price changes
        for h in history:
            labels.append(h.changed_at.strftime('%Y-%m-%d %H:%M'))
            data_points.append(float(h.new_price))
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Unit Price',
                'data': data_points,
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                'tension': 0.1,
                'pointRadius': 4,
                'pointHoverRadius': 6,
                'fill': True
            }]
        }
        
        # Calculate statistics
        all_prices = data_points
        first_price = all_prices[0] if all_prices else float(component.unit_price)
        current_price = float(component.unit_price)
        
        if current_price > first_price:
            trend = 'rising'
        elif current_price < first_price:
            trend = 'falling'
        else:
            trend = 'stable'
        
        statistics = {
            'current_price': current_price,
            'total_changes': len(history),
            'trend': trend,
            'min_price': min(all_prices) if all_prices else current_price,
            'max_price': max(all_prices) if all_prices else current_price,
            'avg_price': sum(all_prices) / len(all_prices) if all_prices else current_price,
            'price_change': current_price - first_price,
            'price_change_percent': ((current_price - first_price) / first_price * 100) if first_price > 0 else 0
        }
    
    # Detailed history for table
    detailed_history = []
    for h in history:
        detailed_history.append({
            'date': h.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'old_price': float(h.old_price) if h.old_price else 0,
            'new_price': float(h.new_price),
            'change_amount': float(h.new_price) - (float(h.old_price) if h.old_price else 0),
            'reason': h.changed_reason or 'No reason provided'
        })
    
    return jsonify({
        'chart_data': chart_data,
        'statistics': statistics,
        'detailed_history': detailed_history,
        'component': {
            'name': component.component_name,
            'part_number': component.part_number or '',
            'description': component.description or ''
        }
    })

@bp.route('/manage/<int:assembly_id>')
def manage_components(assembly_id):
    """Manage components with Excel-like table interface"""
    assembly = Assembly.query.get_or_404(assembly_id)
    return render_template('components/manage.html', assembly=assembly)

@bp.route('/api/list/<int:assembly_id>')
def api_list_components(assembly_id):
    """API endpoint to get assembly parts for table"""
    assembly = Assembly.query.get_or_404(assembly_id)
    assembly_parts = AssemblyPart.query.filter_by(assembly_id=assembly_id).order_by(AssemblyPart.sort_order).all()
    
    return jsonify([{
        'component_id': ap.assembly_part_id,  # Keep this name for backward compatibility
        'assembly_part_id': ap.assembly_part_id,
        'part_id': ap.part_id,
        'component_name': ap.component_name,  # Uses the property from AssemblyPart
        'description': ap.description,  # Uses the property from AssemblyPart
        'part_number': ap.part_number,  # Uses the property from AssemblyPart
        'unit_price': ap.unit_price,  # Uses the property from AssemblyPart
        'quantity': float(ap.quantity),
        'unit_of_measure': ap.unit_of_measure,
        'total_price': ap.total_price,  # Uses the property from AssemblyPart
        'sort_order': ap.sort_order,
        'notes': ap.notes or '',
        'manufacturer': ap.part.manufacturer or '',
        'category': ap.part.category or '',
        'created_at': ap.created_at.strftime('%Y-%m-%d %H:%M'),
        'updated_at': ap.updated_at.strftime('%Y-%m-%d %H:%M')
    } for ap in assembly_parts])

@bp.route('/api/update/<int:component_id>', methods=['PUT'])
@csrf.exempt
def api_update_component(component_id):
    """API endpoint to update an assembly part (component_id is actually assembly_part_id)"""
    try:
        assembly_part = AssemblyPart.query.get_or_404(component_id)
        data = request.get_json()
        
        # Track price changes for the linked part
        old_price = assembly_part.unit_price
        
        # Update assembly-specific fields
        if 'quantity' in data:
            assembly_part.quantity = float(data['quantity'])
        if 'unit_of_measure' in data:
            assembly_part.unit_of_measure = data['unit_of_measure']
        if 'notes' in data:
            assembly_part.notes = data['notes']
        if 'sort_order' in data:
            assembly_part.sort_order = int(data['sort_order'])
        
        # Update the linked part if needed (price changes affect all assemblies using this part)
        if 'unit_price' in data:
            new_price = float(data['unit_price'])
            if old_price != new_price:
                # Track price history for the part
                price_history = PartsPriceHistory(
                    part_id=assembly_part.part_id,
                    old_price=old_price,
                    new_price=new_price,
                    changed_reason='Assembly table edit'
                )
                db.session.add(price_history)
                
                # Update the part price using the new method
                assembly_part.part.update_price(
                    new_price=new_price,
                    reason='Assembly table edit',
                    source='manual'
                )
        
        # Update other part fields if provided (affects all assemblies using this part)
        if 'component_name' in data and data['component_name']:
            assembly_part.part.description = data['component_name']
        if 'part_number' in data:
            assembly_part.part.part_number = data['part_number']
        if 'description' in data:
            # If description is provided, it could be part description or assembly notes
            if data['description'] != (assembly_part.part.description or ''):
                assembly_part.notes = data['description']
        
        assembly_part.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'component': {
                'component_id': assembly_part.assembly_part_id,
                'assembly_part_id': assembly_part.assembly_part_id,
                'part_id': assembly_part.part_id,
                'component_name': assembly_part.component_name,
                'description': assembly_part.description,
                'part_number': assembly_part.part_number,
                'unit_price': assembly_part.unit_price,
                'quantity': float(assembly_part.quantity),
                'unit_of_measure': assembly_part.unit_of_measure,
                'total_price': assembly_part.total_price,
                'sort_order': assembly_part.sort_order,
                'notes': assembly_part.notes or '',
                'updated_at': assembly_part.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/add/<int:assembly_id>', methods=['POST'])
@csrf.exempt
def api_add_component(assembly_id):
    """API endpoint to add a new assembly part"""
    try:
        assembly = Assembly.query.get_or_404(assembly_id)
        data = request.get_json()
        
        # Get next sort order
        max_sort = db.session.query(db.func.max(AssemblyPart.sort_order)).filter_by(assembly_id=assembly_id).scalar() or 0
        
        # Require part_id (must reference existing part from catalog)
        part_id = data.get('part_id')
        if not part_id:
            return jsonify({'success': False, 'error': 'Part ID is required. Must select from existing parts catalog.'}), 400
        
        part = Parts.query.get_or_404(part_id)
        
        assembly_part = AssemblyPart(
            assembly_id=assembly_id,
            part_id=part.part_id,
            quantity=float(data.get('quantity', 1.0)),
            unit_of_measure=data.get('unit_of_measure', 'EA'),
            notes=data.get('notes', ''),
            sort_order=max_sort + 1
        )
        
        db.session.add(assembly_part)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'component': {
                'component_id': assembly_part.assembly_part_id,
                'assembly_part_id': assembly_part.assembly_part_id,
                'part_id': assembly_part.part_id,
                'component_name': assembly_part.component_name,
                'description': assembly_part.description,
                'part_number': assembly_part.part_number,
                'unit_price': assembly_part.unit_price,
                'quantity': float(assembly_part.quantity),
                'unit_of_measure': assembly_part.unit_of_measure,
                'total_price': assembly_part.total_price,
                'sort_order': assembly_part.sort_order,
                'notes': assembly_part.notes or '',
                'created_at': assembly_part.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': assembly_part.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/delete/<int:component_id>', methods=['DELETE'])
@csrf.exempt
def api_delete_component(component_id):
    """API endpoint to delete an assembly part (component_id is actually assembly_part_id)"""
    try:
        assembly_part = AssemblyPart.query.get_or_404(component_id)
        db.session.delete(assembly_part)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/bulk-delete', methods=['POST'])
@csrf.exempt
def api_bulk_delete_components():
    """API endpoint to delete multiple assembly parts"""
    try:
        data = request.get_json()
        component_ids = data.get('component_ids', [])
        
        assembly_parts = AssemblyPart.query.filter(AssemblyPart.assembly_part_id.in_(component_ids)).all()
        for assembly_part in assembly_parts:
            db.session.delete(assembly_part)
        
        db.session.commit()
        
        return jsonify({'success': True, 'deleted_count': len(assembly_parts)})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/duplicate/<int:component_id>', methods=['POST'])
@csrf.exempt
def api_duplicate_component(component_id):
    """API endpoint to duplicate a component"""
    try:
        original = Component.query.get_or_404(component_id)
        
        # Get next sort order
        max_sort = db.session.query(db.func.max(Component.sort_order)).filter_by(assembly_id=original.assembly_id).scalar() or 0
        
        duplicate = Component(
            assembly_id=original.assembly_id,
            component_name=f"{original.component_name} (Copy)",
            description=original.description,
            part_number=original.part_number,
            unit_price=original.unit_price,
            quantity=original.quantity,
            unit_of_measure=original.unit_of_measure,
            sort_order=max_sort + 1
        )
        
        db.session.add(duplicate)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'component': {
                'component_id': duplicate.component_id,
                'component_name': duplicate.component_name,
                'description': duplicate.description or '',
                'part_number': duplicate.part_number or '',
                'unit_price': float(duplicate.unit_price),
                'quantity': float(duplicate.quantity),
                'unit_of_measure': duplicate.unit_of_measure,
                'total_price': duplicate.total_price,
                'sort_order': duplicate.sort_order,
                'created_at': duplicate.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': duplicate.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ================================
# MASTER COMPONENTS DATABASE MANAGEMENT
# ================================

@bp.route('/database')
def master_parts_database():
    """Master parts database management page"""
    return render_template('components/database.html')

@bp.route('/api/database/list')
def api_list_all_parts():
    """API endpoint to get all parts from database"""
    try:
        # Get all parts from the Parts table
        parts = Parts.query.order_by(Parts.updated_at.desc()).all()
        
        return jsonify([{
            'part_id': p.part_id,
            'category': p.category or '',
            'model': p.model or '',
            'rating': p.rating or '',
            'master_item_number': p.master_item_number or '',
            'manufacturer': p.manufacturer or '',
            'part_number': p.part_number or '',
            'upc': p.upc or '',
            'description': p.description or '',
            'price': p.current_price,
            'vendor': p.vendor or '',
            'effective_date': p.effective_date.strftime('%Y-%m-%d') if p.effective_date else '',
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': p.updated_at.strftime('%Y-%m-%d %H:%M')
        } for p in parts])
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/database/update/<int:part_id>', methods=['PUT'])
@csrf.exempt
def api_update_database_part(part_id):
    """API endpoint to update any part in the database"""
    try:
        part = Parts.query.get_or_404(part_id)
        data = request.get_json()
        
        # Debug logging
        print(f"Update request for part {part_id}: {data}")
        
        # Update part fields (non-price)
        part.category = data.get('category', part.category)
        part.model = data.get('model', part.model)
        part.rating = data.get('rating', part.rating)
        part.master_item_number = data.get('master_item_number', part.master_item_number)
        part.manufacturer = data.get('manufacturer', part.manufacturer)
        part.part_number = data.get('part_number', part.part_number)
        part.upc = data.get('upc', part.upc)
        part.description = data.get('description', part.description)
        part.vendor = data.get('vendor', part.vendor)
        
        # Handle price update with new system
        if 'price' in data:
            new_price = float(data.get('price', 0.00))
            part.update_price(
                new_price=new_price,
                reason='Database direct edit',
                source='manual'
            )
        
        # Handle effective_date if provided - update the current price history record
        if 'effective_date' in data and data['effective_date']:
            try:
                new_effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()
                
                # Find the current price history record and update its effective_date
                current_history = db.session.query(PartsPriceHistory)\
                    .filter_by(part_id=part.part_id, is_current=True)\
                    .first()
                
                if current_history:
                    current_history.effective_date = new_effective_date
                else:
                    # If no price history exists, create one with just the effective date
                    price_history = PartsPriceHistory(
                        part_id=part.part_id,
                        old_price=None,
                        new_price=0.00,  # Default price
                        changed_at=datetime.utcnow(),
                        changed_reason="Effective date update via database edit",
                        effective_date=new_effective_date,
                        is_current=True,
                        source="manual"
                    )
                    db.session.add(price_history)
                    
            except ValueError:
                pass  # Keep existing date if format is invalid
        
        part.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'part': {
                'part_id': part.part_id,
                'category': part.category or '',
                'model': part.model or '',
                'rating': part.rating or '',
                'master_item_number': part.master_item_number or '',
                'manufacturer': part.manufacturer or '',
                'part_number': part.part_number or '',
                'upc': part.upc or '',
                'description': part.description or '',
                'price': part.current_price,
                'vendor': part.vendor or '',
                'effective_date': part.effective_date.strftime('%Y-%m-%d') if part.effective_date else '',
                'updated_at': part.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/database/add', methods=['POST'])
@csrf.exempt
def api_add_database_part():
    """API endpoint to add a new part to the database"""
    try:
        data = request.get_json()
        
        part = Parts(
            category=data.get('category', ''),
            model=data.get('model', ''),
            rating=data.get('rating', ''),
            master_item_number=data.get('master_item_number', ''),
            manufacturer=data.get('manufacturer', ''),
            part_number=data.get('part_number', ''),
            upc=data.get('upc', ''),
            description=data.get('description', ''),
            vendor=data.get('vendor', '')
        )
        
        db.session.add(part)
        db.session.flush()  # Get the part_id
        
        # Add price history if price is provided
        price = float(data.get('price', 0.0))
        if price > 0:
            effective_date = None
            if data.get('effective_date'):
                try:
                    effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()
                except ValueError:
                    effective_date = datetime.utcnow().date()  # Default to today
            
            price_history = PartsPriceHistory(
                part_id=part.part_id,
                old_price=None,  # No previous price for new part
                new_price=price,
                changed_at=datetime.utcnow(),
                changed_reason="Initial part creation",
                effective_date=effective_date or datetime.utcnow().date(),
                is_current=True,
                source="manual"
            )
            db.session.add(price_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'part': {
                'part_id': part.part_id,
                'category': part.category or '',
                'model': part.model or '',
                'rating': part.rating or '',
                'master_item_number': part.master_item_number or '',
                'manufacturer': part.manufacturer or '',
                'part_number': part.part_number or '',
                'upc': part.upc or '',
                'description': part.description or '',
                'price': part.current_price,
                'vendor': part.vendor or '',
                'effective_date': part.effective_date.strftime('%Y-%m-%d') if part.effective_date else '',
                'created_at': part.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated_at': part.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/database/delete/<int:part_id>', methods=['DELETE'])
@csrf.exempt
def api_delete_database_part(part_id):
    """API endpoint to delete any part from the database"""
    try:
        part = Parts.query.get_or_404(part_id)
        
        # First delete all assembly_parts that reference this part
        assembly_parts = AssemblyPart.query.filter_by(part_id=part_id).all()
        for assembly_part in assembly_parts:
            db.session.delete(assembly_part)
        
        # Delete all estimate_components that reference this part
        estimate_components = EstimateComponent.query.filter_by(part_id=part_id).all()
        for estimate_component in estimate_components:
            db.session.delete(estimate_component)
        
        # Delete all standard_assembly_components that reference this part
        standard_assembly_components = StandardAssemblyComponent.query.filter_by(part_id=part_id).all()
        for standard_assembly_component in standard_assembly_components:
            db.session.delete(standard_assembly_component)
        
        # Delete all tech_data entries that reference this part
        tech_data_entries = TechData.query.filter_by(part_id=part_id).all()
        for tech_data in tech_data_entries:
            db.session.delete(tech_data)
        
        # Clear VFD references in motors (set to NULL since it's nullable)
        motors_with_vfd = Motor.query.filter_by(selected_vfd_part_id=part_id).all()
        for motor in motors_with_vfd:
            motor.selected_vfd_part_id = None
        
        # Then delete the part itself
        db.session.delete(part)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/database/bulk-delete', methods=['POST'])
@csrf.exempt
def api_bulk_delete_database_parts():
    """API endpoint to delete multiple parts from database"""
    try:
        data = request.get_json()
        part_ids = data.get('part_ids', [])
        
        # First delete all assembly_parts that reference these parts
        assembly_parts = AssemblyPart.query.filter(AssemblyPart.part_id.in_(part_ids)).all()
        for assembly_part in assembly_parts:
            db.session.delete(assembly_part)
        
        # Delete all estimate_components that reference these parts
        estimate_components = EstimateComponent.query.filter(EstimateComponent.part_id.in_(part_ids)).all()
        for estimate_component in estimate_components:
            db.session.delete(estimate_component)
        
        # Delete all standard_assembly_components that reference these parts
        standard_assembly_components = StandardAssemblyComponent.query.filter(StandardAssemblyComponent.part_id.in_(part_ids)).all()
        for standard_assembly_component in standard_assembly_components:
            db.session.delete(standard_assembly_component)
        
        # Delete all tech_data entries that reference these parts
        tech_data_entries = TechData.query.filter(TechData.part_id.in_(part_ids)).all()
        for tech_data in tech_data_entries:
            db.session.delete(tech_data)
        
        # Clear VFD references in motors (set to NULL since it's nullable)
        motors_with_vfd = Motor.query.filter(Motor.selected_vfd_part_id.in_(part_ids)).all()
        for motor in motors_with_vfd:
            motor.selected_vfd_part_id = None
        
        # Then delete the parts themselves
        parts = Parts.query.filter(Parts.part_id.in_(part_ids)).all()
        for part in parts:
            db.session.delete(part)
        
        db.session.commit()
        
        return jsonify({'success': True, 'deleted_count': len(parts)})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/parts/<int:part_id>/price-history')
def parts_price_history(part_id):
    """Show part price history with chart"""
    part = Parts.query.get_or_404(part_id)
    history = PartsPriceHistory.query.filter_by(part_id=part_id).order_by(PartsPriceHistory.changed_at).all()

    return render_template('parts/price_history.html', part=part, history=history)

@bp.route('/parts/<int:part_id>/price-history-data')
def parts_price_history_data(part_id):
    """API endpoint for parts price history chart data with statistics"""
    part = Parts.query.get_or_404(part_id)
    history = PartsPriceHistory.query.filter_by(part_id=part_id).order_by(PartsPriceHistory.changed_at).all()
    
    current_price = part.current_price
    
    if not history:
        # If no history, create a single point with current price
        chart_data = {
            'labels': [part.created_at.strftime('%Y-%m-%d %H:%M')],
            'datasets': [{
                'label': 'Price',
                'data': [current_price],
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                'tension': 0.1,
                'pointRadius': 4,
                'pointHoverRadius': 6
            }]
        }
        
        statistics = {
            'current_price': current_price,
            'total_changes': 0,
            'trend': 'stable',
            'min_price': current_price,
            'max_price': current_price,
            'avg_price': current_price
        }
    else:
        # Create chart data
        labels = []
        data_points = []
        
        # Add creation point if we have history
        if history:
            labels.append(part.created_at.strftime('%Y-%m-%d %H:%M'))
            data_points.append(float(history[0].old_price) if history[0].old_price else current_price)
        
        # Add all price changes
        for h in history:
            labels.append(h.changed_at.strftime('%Y-%m-%d %H:%M'))
            data_points.append(float(h.new_price))
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': 'Price',
                'data': data_points,
                'borderColor': '#007bff',
                'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                'tension': 0.1,
                'pointRadius': 4,
                'pointHoverRadius': 6,
                'fill': True
            }]
        }
        
        # Calculate statistics
        all_prices = data_points
        first_price = all_prices[0] if all_prices else current_price
        
        if current_price > first_price:
            trend = 'rising'
        elif current_price < first_price:
            trend = 'falling'
        else:
            trend = 'stable'
        
        statistics = {
            'current_price': current_price,
            'total_changes': len(history),
            'trend': trend,
            'min_price': min(all_prices) if all_prices else current_price,
            'max_price': max(all_prices) if all_prices else current_price,
            'avg_price': sum(all_prices) / len(all_prices) if all_prices else current_price,
            'price_change': current_price - first_price,
            'price_change_percent': ((current_price - first_price) / first_price * 100) if first_price > 0 else 0
        }
    
    # Detailed history for table
    detailed_history = []
    for h in history:
        detailed_history.append({
            'date': h.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'old_price': float(h.old_price) if h.old_price else 0,
            'new_price': float(h.new_price),
            'change_amount': float(h.new_price) - (float(h.old_price) if h.old_price else 0),
            'reason': h.changed_reason or 'No reason provided'
        })
    
    return jsonify({
        'chart_data': chart_data,
        'statistics': statistics,
        'detailed_history': detailed_history,
        'component': {
            'name': f"{part.part_number} - {part.description}" if part.part_number and part.description else part.part_number or part.description or 'Unknown Part',
            'part_number': part.part_number or '',
            'description': part.description or '',
            'manufacturer': part.manufacturer or '',
            'category': part.category or ''
        }
    })

@bp.route('/api/database/assemblies')
def api_get_assemblies_for_selection():
    """API endpoint to get all assemblies for component creation"""
    try:
        assemblies = db.session.query(Assembly).join(Estimate).join(Project).all()
        
        return jsonify([{
            'assembly_id': a.assembly_id,
            'assembly_name': a.assembly_name,
            'estimate_id': a.estimate_id,
            'estimate_name': a.estimate.estimate_name,
            'estimate_number': a.estimate.estimate_number,
            'project_id': a.estimate.project_id,
            'project_name': a.estimate.project.project_name,
            'client_name': a.estimate.project.client_name
        } for a in assemblies])
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:component_id>/update-quantity', methods=['POST'])
@csrf.exempt
def update_component_quantity(component_id):
    """Update component quantity via AJAX"""
    assembly_part = AssemblyPart.query.get_or_404(component_id)
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format'}), 400
    
    new_quantity = request.json.get('quantity')
    if new_quantity is None:
        return jsonify({'success': False, 'error': 'Quantity is required'}), 400
    
    try:
        new_quantity = float(new_quantity)
        if new_quantity < 0:
            return jsonify({'success': False, 'error': 'Quantity must be at least 0'}), 400
        
        old_quantity = float(assembly_part.quantity)
        assembly_part.quantity = new_quantity
        assembly_part.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Component quantity updated from {old_quantity} to {new_quantity}',
            'old_quantity': old_quantity,
            'new_quantity': new_quantity,
            'new_total': float(new_quantity) * float(assembly_part.unit_price)
        })
        
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid quantity value'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/parts-by-category/<string:category>')
def api_parts_by_category(category):
    """API endpoint to get parts by category for component substitution"""
    try:
        parts = Parts.query.filter_by(category=category)\
            .order_by(Parts.description, Parts.part_number)\
            .all()

        return jsonify([{
            'part_id': p.part_id,
            'part_number': p.part_number or '',
            'description': p.description or '',
            'current_price': float(p.current_price),
            'manufacturer': p.manufacturer or '',
            'model': p.model or '',
            'rating': p.rating or '',
            'vendor': p.vendor or '',
            'display_name': f"{p.part_number or 'No Part Number'} - {p.description or 'No Description'}"
        } for p in parts])

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/database/export-csv')
def export_database_csv():
    """Export all parts from database to CSV files (249 items per file with UPC and quantity columns)"""
    try:
        # Get all parts from database ordered by part_id
        parts = Parts.query.order_by(Parts.part_id).all()

        if not parts:
            flash('No parts found in database to export', 'warning')
            return redirect(url_for('components.master_parts_database'))

        # Define the chunk size
        ITEMS_PER_FILE = 249

        # Create a zip file in memory to hold multiple CSV files
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Split parts into chunks of 249
            for file_num, i in enumerate(range(0, len(parts), ITEMS_PER_FILE), start=1):
                chunk = parts[i:i + ITEMS_PER_FILE]

                # Create CSV in memory for this chunk
                csv_buffer = io.StringIO()
                csv_writer = csv.writer(csv_buffer)

                # Write header row
                csv_writer.writerow(['UPC', 'Quantity'])

                # Write data rows
                for part in chunk:
                    upc = part.upc if part.upc else ''
                    quantity = 1  # Always 1 as per requirement
                    csv_writer.writerow([upc, quantity])

                # Add this CSV to the zip file
                filename = f'parts_export_{file_num}.csv'
                zip_file.writestr(filename, csv_buffer.getvalue())

        # Prepare the zip file for download
        zip_buffer.seek(0)

        # Generate download filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        download_filename = f'parts_export_{timestamp}.zip'

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        flash(f'Error exporting parts to CSV: {str(e)}', 'error')
        return redirect(url_for('components.master_parts_database'))
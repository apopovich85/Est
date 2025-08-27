from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import AssemblyCategory, db
from app import csrf
from datetime import datetime

bp = Blueprint('categories', __name__)

@bp.route('/')
def list_categories():
    """List all assembly categories for management"""
    categories = AssemblyCategory.get_all_categories()
    return render_template('categories/list.html', categories=categories)

@bp.route('/create', methods=['GET', 'POST'])
def create_category():
    """Create a new assembly category"""
    if request.method == 'POST':
        try:
            # Get form data
            code = request.form['code'].strip().upper()
            name = request.form['name'].strip()
            description = request.form.get('description', '').strip()
            sort_order = int(request.form.get('sort_order', 999))
            is_active = 'is_active' in request.form
            
            # Validate required fields
            if not code or not name:
                flash('Code and Name are required fields.', 'error')
                return render_template('categories/create.html')
            
            # Check for duplicate code
            existing = AssemblyCategory.query.filter_by(code=code).first()
            if existing:
                flash(f'Category code "{code}" already exists.', 'error')
                return render_template('categories/create.html')
            
            # Create new category
            category = AssemblyCategory(
                code=code,
                name=name,
                description=description,
                sort_order=sort_order,
                is_active=is_active
            )
            
            db.session.add(category)
            db.session.commit()
            
            flash(f'Category "{code}" created successfully!', 'success')
            return redirect(url_for('categories.list_categories'))
            
        except ValueError:
            flash('Sort order must be a valid number.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating category: {str(e)}', 'error')
    
    return render_template('categories/create.html')

@bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
def edit_category(category_id):
    """Edit an existing assembly category"""
    category = AssemblyCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            code = request.form['code'].strip().upper()
            name = request.form['name'].strip()
            description = request.form.get('description', '').strip()
            sort_order = int(request.form.get('sort_order', 999))
            is_active = 'is_active' in request.form
            
            # Validate required fields
            if not code or not name:
                flash('Code and Name are required fields.', 'error')
                return render_template('categories/edit.html', category=category)
            
            # Check for duplicate code (excluding current category)
            existing = AssemblyCategory.query.filter(
                AssemblyCategory.code == code,
                AssemblyCategory.category_id != category_id
            ).first()
            if existing:
                flash(f'Category code "{code}" already exists.', 'error')
                return render_template('categories/edit.html', category=category)
            
            # Update category
            category.code = code
            category.name = name
            category.description = description
            category.sort_order = sort_order
            category.is_active = is_active
            category.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Category "{code}" updated successfully!', 'success')
            return redirect(url_for('categories.list_categories'))
            
        except ValueError:
            flash('Sort order must be a valid number.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'error')
    
    return render_template('categories/edit.html', category=category)

@bp.route('/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    """Delete an assembly category"""
    category = AssemblyCategory.query.get_or_404(category_id)
    
    try:
        # Check if category is in use
        from app.models import StandardAssembly
        assemblies_using = StandardAssembly.query.filter_by(category=category.code).count()
        
        if assemblies_using > 0:
            flash(f'Cannot delete category "{category.code}" - it is used by {assemblies_using} assemblies.', 'error')
        else:
            db.session.delete(category)
            db.session.commit()
            flash(f'Category "{category.code}" deleted successfully!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('categories.list_categories'))

@bp.route('/<int:category_id>/toggle', methods=['POST'])
def toggle_category(category_id):
    """Toggle active status of a category"""
    category = AssemblyCategory.query.get_or_404(category_id)
    
    try:
        category.is_active = not category.is_active
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = "activated" if category.is_active else "deactivated"
        flash(f'Category "{category.code}" {status} successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating category: {str(e)}', 'error')
    
    return redirect(url_for('categories.list_categories'))

# API endpoint for getting active categories (used by other forms)
@bp.route('/api/active')
def api_active_categories():
    """Get all active categories for use in forms"""
    categories = AssemblyCategory.get_active_categories()
    return jsonify([{
        'code': cat.code,
        'name': cat.name,
        'description': cat.description
    } for cat in categories])
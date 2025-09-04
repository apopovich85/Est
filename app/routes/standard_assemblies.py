from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import StandardAssembly, StandardAssemblyComponent, AssemblyVersion, Parts, Assembly, AssemblyPart, Estimate, Project, AssemblyCategory, PartCategory
from app import db, csrf
from datetime import datetime
from sqlalchemy import or_, and_, func

bp = Blueprint('standard_assemblies', __name__)

@bp.route('/')
def list_assemblies():
    """List all standard assemblies with filtering"""
    category_filter = request.args.get('category', '')
    search_filter = request.args.get('search', '')
    active_only = request.args.get('active', 'true') == 'true'
    
    query = StandardAssembly.query
    
    # Filter by active status
    if active_only:
        query = query.filter(StandardAssembly.is_active == True)
    
    # Filter by template status (show only current templates, not all versions)
    query = query.filter(StandardAssembly.is_template == True)
    
    # Apply category filter
    if category_filter:
        query = query.join(AssemblyCategory).filter(AssemblyCategory.code == category_filter)
    
    # Apply search filter
    if search_filter:
        query = query.filter(
            or_(
                StandardAssembly.name.ilike(f'%{search_filter}%'),
                StandardAssembly.description.ilike(f'%{search_filter}%')
            )
        )
    
    assemblies = query.order_by(StandardAssembly.name).all()
    
    # Get available categories from database
    categories = AssemblyCategory.get_active_categories()
    
    return render_template('standard_assemblies/list.html', 
                         assemblies=assemblies, 
                         categories=categories,
                         current_category=category_filter,
                         current_search=search_filter,
                         active_only=active_only)

@bp.route('/import', methods=['GET', 'POST'])
def import_assemblies():
    """Import assemblies from CSV file"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.csv'):
            try:
                import csv
                import io
                
                # Read CSV content and handle BOM
                content = file.stream.read()
                
                # Try different encodings and handle BOM
                try:
                    decoded_content = content.decode('utf-8-sig')  # Handles BOM automatically
                except UnicodeDecodeError:
                    try:
                        decoded_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        decoded_content = content.decode('latin1')
                
                stream = io.StringIO(decoded_content, newline=None)
                csv_reader = csv.DictReader(stream)
                
                # Get and clean column names
                fieldnames = csv_reader.fieldnames
                if not fieldnames:
                    flash('CSV file appears to be empty or invalid', 'error')
                    return redirect(request.url)
                
                # Clean column names (remove quotes and whitespace)
                cleaned_fieldnames = [name.strip(' "') for name in fieldnames]
                
                # Check for required columns
                required_cols = ['AssemblyCat', 'Assembly_ID', 'Component_Part_Number', 'Quantity']
                missing_cols = [col for col in required_cols if col not in cleaned_fieldnames]
                
                if missing_cols:
                    flash(f'Missing required columns: {", ".join(missing_cols)}. Found columns: {", ".join(cleaned_fieldnames)}', 'error')
                    return redirect(request.url)
                
                assemblies_data = {}
                row_count = 0
                
                # Process CSV rows
                for row in csv_reader:
                    row_count += 1
                    
                    # Clean row data (remove quotes and whitespace)
                    cleaned_row = {}
                    for original_key, value in row.items():
                        clean_key = original_key.strip(' "')
                        cleaned_row[clean_key] = value.strip(' "') if isinstance(value, str) else value
                    
                    try:
                        assembly_id = cleaned_row.get('Assembly_ID', '').strip()
                        category = cleaned_row.get('AssemblyCat', '').strip()
                        part_number = cleaned_row.get('Component_Part_Number', '').strip()
                        quantity_str = cleaned_row.get('Quantity', '1').strip()
                        
                        # Skip empty rows
                        if not assembly_id or not part_number:
                            continue
                            
                        try:
                            quantity = float(quantity_str) if quantity_str else 1.0
                        except (ValueError, TypeError):
                            quantity = 1.0
                        
                        if assembly_id not in assemblies_data:
                            assemblies_data[assembly_id] = {
                                'name': assembly_id,
                                'category': category,
                                'components': []
                            }
                        
                        assemblies_data[assembly_id]['components'].append({
                            'part_number': part_number,
                            'quantity': quantity
                        })
                        
                    except Exception as row_error:
                        print(f"Error processing row {row_count}: {row_error}")
                        continue
                
                if not assemblies_data:
                    flash('No valid assembly data found in CSV file', 'error')
                    return redirect(request.url)
                
                flash(f'Successfully parsed {len(assemblies_data)} assemblies from CSV file', 'success')
                
                return render_template('standard_assemblies/import_preview.html', 
                                     assemblies_data=assemblies_data)
                
            except Exception as e:
                flash(f'Error processing CSV file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Please upload a CSV file', 'error')
            return redirect(request.url)
    
    return render_template('standard_assemblies/import.html')

@bp.route('/import/process', methods=['POST'])
@csrf.exempt
def process_import():
    """Process the import data and create assemblies"""
    try:
        import json
        
        assemblies_data = json.loads(request.form.get('assemblies_data', '{}'))
        selected_assemblies_str = request.form.get('selected_assemblies', '')
        selected_assemblies = selected_assemblies_str.split(',') if selected_assemblies_str else []
        
        created_count = 0
        skipped_count = 0
        for assembly_id in selected_assemblies:
            if assembly_id in assemblies_data:
                data = assemblies_data[assembly_id]
                
                # Check for duplicate by assembly_number if available
                assembly_number = data.get('assembly_number', assembly_id)
                existing = StandardAssembly.query.filter_by(assembly_number=assembly_number).first()
                
                if existing:
                    print(f"SKIP {data['name']} ({assembly_number}) - already exists")
                    skipped_count += 1
                    continue
                
                # Get or create category
                category_name = data['category']
                category = AssemblyCategory.query.filter_by(name=category_name).first()
                if not category:
                    # Create category if it doesn't exist
                    category = AssemblyCategory(
                        code=category_name.upper().replace(' ', '_'),
                        name=category_name,
                        description=f"Imported category: {category_name}",
                        is_active=True
                    )
                    db.session.add(category)
                    db.session.flush()
                
                # Create standard assembly
                assembly = StandardAssembly(
                    name=data['name'],
                    assembly_number=assembly_number,
                    category_id=category.category_id,
                    description=f"Imported from CSV - {data['category']} assembly",
                    version="1.0",
                    is_active=True,
                    is_template=True,
                    created_by="System Import"
                )
                
                db.session.add(assembly)
                db.session.flush()  # Get the ID
                
                # Add components
                for i, comp_data in enumerate(data['components']):
                    # Try to find existing part or create placeholder
                    part = Parts.query.filter_by(part_number=comp_data['part_number']).first()
                    
                    if not part:
                        # Create placeholder part
                        part = Parts(
                            part_number=comp_data['part_number'],
                            description=f"Imported part - {comp_data['part_number']}",
                            manufacturer="Unknown",
                            category="Imported",
                            price=0.00
                        )
                        db.session.add(part)
                        db.session.flush()
                    
                    # Add component to assembly
                    component = StandardAssemblyComponent(
                        standard_assembly_id=assembly.standard_assembly_id,
                        part_id=part.part_id,
                        quantity=comp_data['quantity'],
                        unit_of_measure='EA',
                        sort_order=i + 1
                    )
                    db.session.add(component)
                
                created_count += 1
        
        db.session.commit()
        if skipped_count > 0:
            flash(f'Successfully imported {created_count} assemblies, skipped {skipped_count} duplicates', 'success')
        else:
            flash(f'Successfully imported {created_count} assemblies', 'success')
        return redirect(url_for('standard_assemblies.list_assemblies'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing assemblies: {str(e)}', 'error')
        return redirect(url_for('standard_assemblies.import_assemblies'))

@bp.route('/create', methods=['GET', 'POST'])
def create_assembly():
    """Create a new standard assembly"""
    if request.method == 'POST':
        try:
            # Look up the category by code to get the category_id
            category_code = request.form['category']
            category = AssemblyCategory.query.filter_by(code=category_code, is_active=True).first()
            if not category:
                flash(f'Invalid category selected: {category_code}', 'error')
                categories = AssemblyCategory.get_active_categories()
                return render_template('standard_assemblies/create.html', categories=categories)
            
            assembly = StandardAssembly(
                name=request.form['name'],
                description=request.form.get('description', ''),
                category_id=category.category_id,
                version='1.0',
                is_active=True,
                is_template=True,
                created_by=request.form.get('created_by', 'System')
            )
            
            db.session.add(assembly)
            db.session.flush()  # Get the ID
            
            # Create initial version record
            version_record = AssemblyVersion(
                standard_assembly_id=assembly.standard_assembly_id,
                version_number='1.0',
                notes='Initial version',
                created_by=assembly.created_by
            )
            
            db.session.add(version_record)
            db.session.commit()
            
            flash(f'Standard assembly "{assembly.name}" created successfully!', 'success')
            return redirect(url_for('standard_assemblies.edit_assembly', assembly_id=assembly.standard_assembly_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating standard assembly: {str(e)}', 'error')
    
    # Get active categories from database
    categories = AssemblyCategory.get_active_categories()
    
    return render_template('standard_assemblies/create.html', categories=categories)

@bp.route('/<int:assembly_id>')
def view_assembly(assembly_id):
    """View standard assembly details"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    return render_template('standard_assemblies/view.html', assembly=assembly)

@bp.route('/<int:assembly_id>/edit')
def edit_assembly(assembly_id):
    """Edit standard assembly with drag-and-drop interface"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    
    # Get existing categories for filtering parts
    categories = db.session.query(PartCategory.name).distinct().all()
    part_categories = sorted([cat[0] for cat in categories if cat[0]])
    
    return render_template('standard_assemblies/edit.html', 
                         assembly=assembly,
                         part_categories=part_categories)

@bp.route('/<int:assembly_id>/versions')
def view_versions(assembly_id):
    """View version history for a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    versions = assembly.get_version_history()
    
    # Find the current template version
    current_template = None
    for version in versions:
        if version.is_template:
            current_template = version
            break
    
    # If no template found in versions, use the assembly itself
    if not current_template:
        current_template = assembly
    
    return render_template('standard_assemblies/versions.html', 
                         assembly=current_template, 
                         versions=versions)

@bp.route('/<int:assembly_id>/create-version', methods=['POST'])
def create_version(assembly_id):
    """Create a new version of a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    
    try:
        notes = request.form.get('notes', '')
        new_version = assembly.create_new_version(notes)
        db.session.commit()
        
        flash(f'New version {new_version.version} created successfully!', 'success')
        return redirect(url_for('standard_assemblies.edit_assembly', assembly_id=new_version.standard_assembly_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating new version: {str(e)}', 'error')
        return redirect(url_for('standard_assemblies.view_assembly', assembly_id=assembly_id))

@bp.route('/apply')
def apply_interface():
    """Interface to apply standard assemblies to estimates"""
    project_id = request.args.get('project_id')
    estimate_id = request.args.get('estimate_id')
    
    # Get projects and estimates for selection
    projects = Project.query.order_by(Project.project_name).all()
    
    estimates = []
    if project_id:
        estimates = Estimate.query.filter_by(project_id=project_id).order_by(Estimate.estimate_name).all()
    elif estimate_id:
        estimate = Estimate.query.get(estimate_id)
        if estimate:
            estimates = [estimate]
            project_id = estimate.project_id
    
    # Get active standard assemblies
    assemblies = StandardAssembly.query.join(AssemblyCategory).filter(
        and_(
            StandardAssembly.is_active == True,
            StandardAssembly.is_template == True
        )
    ).order_by(AssemblyCategory.name, StandardAssembly.name).all()
    
    return render_template('standard_assemblies/apply.html',
                         projects=projects,
                         estimates=estimates,
                         assemblies=assemblies,
                         selected_project_id=int(project_id) if project_id else None,
                         selected_estimate_id=int(estimate_id) if estimate_id else None)

@bp.route('/apply/<int:assembly_id>/to/<int:estimate_id>', methods=['POST'])
@csrf.exempt
def apply_to_estimate(assembly_id, estimate_id):
    """Apply a standard assembly to an estimate with optional quantity multiplier"""
    try:
        standard_assembly = StandardAssembly.query.get_or_404(assembly_id)
        estimate = Estimate.query.get_or_404(estimate_id)
        
        # Get quantity from request data
        quantity_multiplier = 1
        if request.is_json and request.json:
            quantity_multiplier = max(1, int(request.json.get('quantity', 1)))
            print(f"DEBUG: Received quantity: {quantity_multiplier}")
        else:
            print(f"DEBUG: No JSON data received. Content-Type: {request.content_type}")
    except Exception as e:
        print(f"ERROR: Exception in apply_to_estimate setup: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Setup error: {str(e)}'}), 500
    
    try:
        # Get highest sort order for this estimate
        max_sort = db.session.query(func.max(Assembly.sort_order))\
            .filter_by(estimate_id=estimate_id).scalar() or 0
        
        # Create assembly name with quantity if > 1
        assembly_name = standard_assembly.name
        if quantity_multiplier > 1:
            assembly_name = f"{standard_assembly.name} (x{quantity_multiplier})"
            
        description = f"{standard_assembly.description}\n(Applied from Standard Assembly v{standard_assembly.version}"
        if quantity_multiplier > 1:
            description += f" with quantity {quantity_multiplier}"
        description += ")"
        
        # Create new assembly in the estimate
        new_assembly = Assembly(
            estimate_id=estimate_id,
            assembly_name=assembly_name,
            description=description,
            sort_order=max_sort + 1,
            standard_assembly_id=standard_assembly.standard_assembly_id,
            standard_assembly_version=standard_assembly.version,
            quantity=quantity_multiplier
        )
        
        db.session.add(new_assembly)
        db.session.flush()  # Get the assembly ID
        
        # Copy all components from standard assembly with quantity multiplier
        for std_component in standard_assembly.components:
            assembly_part = AssemblyPart(
                assembly_id=new_assembly.assembly_id,
                part_id=std_component.part_id,
                quantity=std_component.quantity * quantity_multiplier,
                unit_of_measure=std_component.unit_of_measure,
                notes=std_component.notes,
                sort_order=std_component.sort_order
            )
            db.session.add(assembly_part)
        
        db.session.commit()
        
        # Create success message based on quantity
        message = f'Standard assembly "{standard_assembly.name}"'
        if quantity_multiplier > 1:
            message += f' (x{quantity_multiplier})'
        message += ' applied to estimate successfully!'
        
        flash(message, 'success')
        return jsonify({
            'success': True,
            'message': 'Assembly applied successfully',
            'quantity': quantity_multiplier,
            'assembly_id': new_assembly.assembly_id,
            'estimate_url': url_for('estimates.detail_estimate', estimate_id=estimate_id)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error applying assembly: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

# API Endpoints for AJAX functionality

def analyze_version_differences(version1_components, version2_components):
    """Analyze differences between two component lists"""
    # Create lookup dictionaries for easier comparison
    v1_parts = {comp['part_number']: comp for comp in version1_components}
    v2_parts = {comp['part_number']: comp for comp in version2_components}
    
    added = []      # Components in version2 but not in version1
    removed = []    # Components in version1 but not in version2
    modified = []   # Components that exist in both but have changes
    unchanged = []  # Components that are identical
    
    # Find removed components (in v1 but not v2)
    for part_num, comp in v1_parts.items():
        if part_num not in v2_parts:
            removed.append(comp)
    
    # Find added and modified components
    for part_num, v2_comp in v2_parts.items():
        if part_num not in v1_parts:
            # Component was added
            added.append(v2_comp)
        else:
            # Component exists in both versions, check for changes
            v1_comp = v1_parts[part_num]
            changes = []
            
            if v1_comp['quantity'] != v2_comp['quantity']:
                changes.append(f"Quantity: {v1_comp['quantity']} → {v2_comp['quantity']}")
            
            if v1_comp['unit_price'] != v2_comp['unit_price']:
                changes.append(f"Unit Price: ${v1_comp['unit_price']:.2f} → ${v2_comp['unit_price']:.2f}")
            
            if v1_comp['notes'] != v2_comp['notes']:
                changes.append(f"Notes: '{v1_comp['notes']}' → '{v2_comp['notes']}'")
            
            if changes:
                v2_comp['changes'] = changes
                modified.append(v2_comp)
            else:
                unchanged.append(v2_comp)
    
    return {
        'added': added,
        'removed': removed,
        'modified': modified,
        'unchanged': unchanged
    }

@bp.route('/api/compare/<int:version1_id>/<int:version2_id>')
def api_compare_versions(version1_id, version2_id):
    """Compare two versions of standard assemblies"""
    try:
        version1 = StandardAssembly.query.get_or_404(version1_id)
        version2 = StandardAssembly.query.get_or_404(version2_id)
        
        # Get components for both versions
        version1_components = []
        for comp in version1.components:
            version1_components.append({
                'component_id': comp.component_id,
                'part_id': comp.part_id,
                'part_number': comp.part_number,
                'description': comp.component_name,
                'quantity': float(comp.quantity),
                'unit_of_measure': comp.unit_of_measure,
                'unit_price': float(comp.unit_price),
                'total_price': float(comp.total_price),
                'notes': comp.notes or ''
            })
        
        version2_components = []
        for comp in version2.components:
            version2_components.append({
                'component_id': comp.component_id,
                'part_id': comp.part_id,
                'part_number': comp.part_number,
                'description': comp.component_name,
                'quantity': float(comp.quantity),
                'unit_of_measure': comp.unit_of_measure,
                'unit_price': float(comp.unit_price),
                'total_price': float(comp.total_price),
                'notes': comp.notes or ''
            })
        
        # Analyze differences between versions
        comparison_analysis = analyze_version_differences(version1_components, version2_components)
        
        # Create comparison data
        comparison_data = {
            'version1': {
                'id': version1.standard_assembly_id,
                'version': version1.version,
                'name': version1.name,
                'total_cost': float(version1.total_cost),
                'components': version1_components
            },
            'version2': {
                'id': version2.standard_assembly_id,
                'version': version2.version,
                'name': version2.name,
                'total_cost': float(version2.total_cost),
                'components': version2_components
            },
            'comparison': comparison_analysis
        }
        
        return jsonify(comparison_data)
        
    except Exception as e:
        print(f"Error comparing versions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/<int:assembly_id>/components')
def api_get_components(assembly_id):
    """Get components for a standard assembly"""
    try:
        assembly = StandardAssembly.query.get_or_404(assembly_id)
        
        components = []
        # Sort components by sort_order
        sorted_components = sorted(assembly.components, key=lambda x: x.sort_order or 0)
        for comp in sorted_components:
            try:
                component_data = {
                    'component_id': comp.component_id,
                    'part_id': comp.part_id,
                    'part_number': comp.part_number,
                    'component_name': comp.component_name,
                    'description': comp.description,
                    'quantity': float(comp.quantity),
                    'unit_of_measure': comp.unit_of_measure,
                    'unit_price': comp.unit_price,
                    'total_price': comp.total_price,
                    'manufacturer': comp.part.manufacturer if comp.part else 'Unknown',
                    'category': comp.part.category if comp.part else 'Unknown',
                    'notes': comp.notes or '',
                    'sort_order': comp.sort_order
                }
                components.append(component_data)
            except Exception as e:
                # Skip problematic components but continue processing
                continue
        
        return jsonify(components)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/<int:assembly_id>/add-component', methods=['POST'])
@csrf.exempt
def api_add_component(assembly_id):
    """Add a component to a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    data = request.get_json()
    
    try:
        # Get next sort order
        max_sort = db.session.query(func.max(StandardAssemblyComponent.sort_order))\
            .filter_by(standard_assembly_id=assembly_id).scalar() or 0
        
        component = StandardAssemblyComponent(
            standard_assembly_id=assembly_id,
            part_id=data['part_id'],
            quantity=float(data.get('quantity', 1.0)),
            unit_of_measure=data.get('unit_of_measure', 'EA'),
            notes=data.get('notes', ''),
            sort_order=max_sort + 1
        )
        
        db.session.add(component)
        db.session.commit()
        
        # Return the created component data
        return jsonify({
            'success': True,
            'component': {
                'component_id': component.component_id,
                'part_id': component.part_id,
                'part_number': component.part_number,
                'component_name': component.component_name,
                'description': component.description,
                'quantity': float(component.quantity),
                'unit_of_measure': component.unit_of_measure,
                'unit_price': component.unit_price,
                'total_price': component.total_price,
                'manufacturer': component.part.manufacturer,
                'category': component.part.category,
                'notes': component.notes or '',
                'sort_order': component.sort_order
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/components/<int:component_id>/update', methods=['PUT'])
@csrf.exempt
def api_update_component(component_id):
    """Update a component in a standard assembly"""
    component = StandardAssemblyComponent.query.get_or_404(component_id)
    data = request.get_json()
    
    try:
        if 'quantity' in data:
            component.quantity = float(data['quantity'])
        if 'unit_of_measure' in data:
            component.unit_of_measure = data['unit_of_measure']
        if 'notes' in data:
            component.notes = data['notes']
        if 'sort_order' in data:
            component.sort_order = int(data['sort_order'])
        
        component.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'component': {
                'component_id': component.component_id,
                'quantity': float(component.quantity),
                'unit_of_measure': component.unit_of_measure,
                'notes': component.notes or '',
                'sort_order': component.sort_order,
                'total_price': component.total_price,
                'updated_at': component.updated_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/components/<int:component_id>/delete', methods=['DELETE'])
@csrf.exempt
def api_delete_component(component_id):
    """Delete a component from a standard assembly"""
    component = StandardAssemblyComponent.query.get_or_404(component_id)
    
    try:
        db.session.delete(component)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/<int:assembly_id>/update-name', methods=['PUT'])
@csrf.exempt
def api_update_assembly_name(assembly_id):
    """Update the name of a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    data = request.get_json()
    
    try:
        new_name = data.get('name', '').strip()
        if not new_name:
            return jsonify({'success': False, 'error': 'Name cannot be empty'}), 400
            
        assembly.name = new_name
        assembly.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'name': new_name})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/<int:assembly_id>/update-category', methods=['PUT'])
@csrf.exempt
def api_update_assembly_category(assembly_id):
    """Update the category of a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    data = request.get_json()
    
    try:
        new_category = data.get('category', '').strip()
        if not new_category:
            return jsonify({'success': False, 'error': 'Category cannot be empty'}), 400
        
        # Verify the category exists
        category = AssemblyCategory.query.filter_by(code=new_category, is_active=True).first()
        if not category:
            return jsonify({'success': False, 'error': 'Invalid category selected'}), 400
            
        assembly.category_id = category.category_id
        assembly.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'category': new_category})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/<int:assembly_id>/update-description', methods=['PUT'])
@csrf.exempt
def api_update_assembly_description(assembly_id):
    """Update the description of a standard assembly"""
    assembly = StandardAssembly.query.get_or_404(assembly_id)
    data = request.get_json()
    
    try:
        new_description = data.get('description', '').strip()
        assembly.description = new_description
        assembly.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'description': new_description})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@bp.route('/api/parts/search')
def api_search_parts():
    """Search parts for drag-and-drop interface"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    limit = int(request.args.get('limit', 100))
    
    parts_query = Parts.query
    
    # Apply filters
    if query:
        parts_query = parts_query.filter(
            or_(
                Parts.description.ilike(f'%{query}%'),
                Parts.part_number.ilike(f'%{query}%'),
                Parts.model.ilike(f'%{query}%')
            )
        )
    
    if category:
        parts_query = parts_query.join(PartCategory).filter(PartCategory.name == category)
    
    if manufacturer:
        parts_query = parts_query.filter(Parts.manufacturer == manufacturer)
    
    parts = parts_query.limit(limit).all()
    
    return jsonify([{
        'part_id': part.part_id,
        'part_number': part.part_number or '',
        'description': part.description or '',
        'manufacturer': part.manufacturer or '',
        'category': part.category or '',
        'price': part.current_price,
        'model': part.model or '',
        'rating': part.rating or ''
    } for part in parts])

@bp.route('/api/categories')
def api_get_categories():
    """Get all categories for filtering"""
    # Get assembly categories from the AssemblyCategory table
    assembly_categories = AssemblyCategory.query.filter_by(is_active=True).all()
    assembly_cat_names = [cat.name for cat in assembly_categories]
    
    # Get part categories (these are still strings in the parts table)
    part_categories = db.session.query(Parts.category).distinct().all()
    part_cat_names = [cat[0] for cat in part_categories if cat[0]]
    
    all_categories = set()
    all_categories.update(assembly_cat_names)
    all_categories.update(part_cat_names)
    
    return jsonify(sorted(list(all_categories)))

@bp.route('/api/estimates/<int:project_id>')
def api_get_project_estimates(project_id):
    """Get estimates for a project (for apply interface)"""
    estimates = Estimate.query.filter_by(project_id=project_id).order_by(Estimate.estimate_name).all()
    
    return jsonify([{
        'estimate_id': est.estimate_id,
        'estimate_name': est.estimate_name,
        'estimate_number': est.estimate_number
    } for est in estimates])

# Additional API endpoints for list template
@bp.route('/api/projects/list')
def api_get_all_projects():
    """Get all projects for apply interface"""
    projects = Project.query.order_by(Project.project_name).all()
    
    return jsonify([{
        'project_id': project.project_id,
        'project_name': project.project_name,
        'client_name': project.client_name
    } for project in projects])


@bp.route('/bulk-delete', methods=['DELETE'])
@csrf.exempt
def bulk_delete_assemblies():
    """Delete multiple standard assemblies"""
    data = request.get_json()
    if not data or 'assembly_ids' not in data:
        return jsonify({'success': False, 'error': 'No assembly IDs provided'}), 400
    
    assembly_ids = data['assembly_ids']
    if not assembly_ids:
        return jsonify({'success': False, 'error': 'No assembly IDs provided'}), 400
    
    try:
        deleted_count = 0
        skipped_count = 0
        skipped_assemblies = []
        
        for assembly_id in assembly_ids:
            assembly = StandardAssembly.query.get(assembly_id)
            if not assembly:
                continue
                
            # Check if assembly is being used in any estimates
            estimates_using = Assembly.query.filter_by(standard_assembly_id=assembly_id).count()
            if estimates_using > 0:
                skipped_assemblies.append(f"{assembly.name} (used in {estimates_using} estimate(s))")
                skipped_count += 1
                continue
            
            # Safe to delete
            db.session.delete(assembly)
            deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'skipped_details': skipped_assemblies,
            'message': f'Deleted {deleted_count} assemblies' + (f', skipped {skipped_count}' if skipped_count > 0 else '')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
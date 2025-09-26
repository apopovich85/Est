from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Parts, PartsPriceHistory, PartCategory
from app import db, csrf
import csv
import os
import pandas as pd
from datetime import datetime
from decimal import Decimal

bp = Blueprint('parts', __name__)

def clean_field_value(value):
    """Clean field value and return None for empty/whitespace-only strings"""
    if value is None:
        return None
    
    # Convert to string and handle pandas NaN
    if pd.isna(value):
        return None
    
    # Convert to string and strip whitespace
    cleaned = str(value).strip()
    
    # Return None for empty strings or common placeholder values
    if not cleaned or cleaned.lower() in ['', 'null', 'none', 'n/a', 'na', '#n/a']:
        return None
    
    return cleaned

@bp.route('/import', methods=['GET', 'POST'])
@csrf.exempt
def import_parts():
    """Import parts from uploaded file"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            flash('Please select a CSV or Excel file', 'error')
            return redirect(request.url)
        
        try:
            imported_count = 0
            error_count = 0
            duplicate_count = 0
            duplicate_items = []
            
            # Handle different file types
            if file.filename.lower().endswith(('.xlsx', '.xls')):
                # Handle Excel file
                import tempfile
                import pandas as pd
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                    temp_file_path = temp_file.name
                
                try:
                    file.save(temp_file_path)
                    df = pd.read_excel(temp_file_path)
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                
                if df.empty:
                    flash('Excel file appears to be empty', 'error')
                    return redirect(request.url)
                
                # Convert to dict records for processing
                rows = df.to_dict('records')
                
            else:
                # Handle CSV file
                content = file.stream.read()
                
                # Handle BOM and encoding
                if content.startswith(b'\\xef\\xbb\\xbf'):
                    content = content[3:]  # Remove BOM
                
                decoded_content = content.decode('utf-8-sig')
                csv_lines = decoded_content.splitlines()
                
                if len(csv_lines) < 2:  # Header + at least one data row
                    flash('File appears to be empty or invalid', 'error')
                    return redirect(request.url)
                
                # Parse file
                reader = csv.DictReader(csv_lines)
                rows = list(reader)
            
            # Process each row
            for row in rows:
                try:
                    # Convert pandas NaN to empty string for Excel files
                    if file.filename.lower().endswith(('.xlsx', '.xls')):
                        row = {k: str(v) if pd.notna(v) else '' for k, v in row.items()}
                    
                    # Skip empty rows
                    if not any(str(v).strip() for v in row.values()):
                        continue
                    
                    # Clean price field (remove commas and quotes) - check multiple possible column names
                    price_str = str(row.get('Unit Price', '') or row.get('price', '') or row.get('Price', '') or '0').replace(',', '').replace('"', '').strip()
                    
                    # Parse effective date with multiple formats
                    effective_date = None
                    if row.get('effective_date'):
                        date_str = str(row.get('effective_date')).strip()
                        if date_str:
                            try:
                                # Try different date formats
                                for date_format in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']:
                                    try:
                                        effective_date = datetime.strptime(date_str, date_format).date()
                                        break
                                    except ValueError:
                                        continue
                            except ValueError:
                                pass  # Skip invalid dates
                    
                    # Create part record with flexible column name mapping
                    part = Parts(
                        category=str(row.get('Category', '') or row.get('category', '')).strip(),
                        model=str(row.get('Model', '') or row.get('model', '')).strip() or None,
                        rating=str(row.get('Rating', '') or row.get('rating', '')).strip() or None,
                        master_item_number=clean_field_value(row.get('Customer Part Number', '')),
                        manufacturer=str(row.get('Manufacturer', '') or row.get('manu', '') or row.get('manufacturer', '')).strip(),
                        part_number=str(row.get('SKU', '') or row.get('part_number', '')).strip(),
                        upc=str(row.get('UPC', '') or row.get('upc', '')).strip() or None,
                        description=str(row.get('Description', '') or row.get('description', '')).strip(),
                        vendor=str(row.get('vendor', '')).strip() or None
                    )
                    
                    # Validate required fields
                    if not part.manufacturer or not part.part_number:
                        error_count += 1
                        continue
                    
                    # Check for existing parts and update if fields have changed
                    existing_part = Parts.query.filter_by(part_number=part.part_number).first()
                    if existing_part:
                        # Compare fields and track changes
                        changes = []
                        updated = False
                        
                        # Compare each field - only update if provided in import data
                        # Only update category if it's provided in the import file
                        import_category = row.get('Category', '') or row.get('category', '')
                        if import_category.strip() and existing_part.category != part.category:
                            changes.append(f"Category: '{existing_part.category}' → '{part.category}'")
                            existing_part.category = part.category
                            updated = True
                            
                        # Only update model if it's provided in the import file
                        import_model = row.get('Model', '') or row.get('model', '')
                        if import_model.strip() and existing_part.model != part.model:
                            changes.append(f"Model: '{existing_part.model}' → '{part.model}'")
                            existing_part.model = part.model
                            updated = True
                            
                        # Only update rating if it's provided in the import file
                        import_rating = row.get('Rating', '') or row.get('rating', '')
                        if import_rating.strip() and existing_part.rating != part.rating:
                            changes.append(f"Rating: '{existing_part.rating}' → '{part.rating}'")
                            existing_part.rating = part.rating
                            updated = True
                            
                        if existing_part.master_item_number != part.master_item_number:
                            changes.append(f"Customer Part Number: '{existing_part.master_item_number}' → '{part.master_item_number}'")
                            existing_part.master_item_number = part.master_item_number
                            updated = True
                            
                        if existing_part.manufacturer != part.manufacturer:
                            changes.append(f"Manufacturer: '{existing_part.manufacturer}' → '{part.manufacturer}'")
                            existing_part.manufacturer = part.manufacturer
                            updated = True
                            
                        if existing_part.upc != part.upc:
                            changes.append(f"UPC: '{existing_part.upc}' → '{part.upc}'")
                            existing_part.upc = part.upc
                            updated = True
                            
                        if existing_part.description != part.description:
                            changes.append(f"Description: '{existing_part.description[:50]}...' → '{part.description[:50]}...'")
                            existing_part.description = part.description
                            updated = True
                            
                        if existing_part.vendor != part.vendor:
                            changes.append(f"Vendor: '{existing_part.vendor}' → '{part.vendor}'")
                            existing_part.vendor = part.vendor
                            updated = True
                        
                        if updated:
                            existing_part.updated_at = datetime.utcnow()
                            imported_count += 1  # Count as import since we updated it
                            
                            # Log the update for duplicate report
                            duplicate_items.append({
                                'part_number': part.part_number,
                                'action': 'updated',
                                'manufacturer': part.manufacturer,
                                'description': part.description,
                                'changes': changes[:3]  # Show first 3 changes to avoid too long text
                            })
                        else:
                            # No changes, count as duplicate skip
                            duplicate_count += 1
                            duplicate_items.append({
                                'part_number': part.part_number,
                                'action': 'skipped',
                                'manufacturer': part.manufacturer,
                                'description': part.description,
                                'existing_manufacturer': existing_part.manufacturer,
                                'existing_description': existing_part.description
                            })
                        
                        # Handle price update for existing part
                        if price_str and price_str != '0' and price_str != 'nan':
                            try:
                                price_value = float(price_str)
                                if price_value > 0 and float(existing_part.current_price) != price_value:
                                    existing_part.update_price(
                                        new_price=price_value,
                                        reason="Updated from file import",
                                        source="file_import",
                                        effective_date=effective_date or datetime.utcnow().date()
                                    )
                            except ValueError:
                                pass  # Skip invalid prices
                        
                        continue  # Skip creating new part since we handled existing one
                    
                    db.session.add(part)
                    db.session.flush()  # Get the part_id
                    
                    # Add price history if price is provided
                    if price_str and price_str != '0' and price_str != 'nan':
                        try:
                            price_value = float(price_str)
                            if price_value > 0:
                                price_history = PartsPriceHistory(
                                    part_id=part.part_id,
                                    old_price=None,  # No previous price for new part
                                    new_price=price_value,
                                    changed_at=datetime.utcnow(),
                                    changed_reason="Initial import from file",
                                    effective_date=effective_date or datetime.utcnow().date(),
                                    is_current=True,
                                    source="file_import"
                                )
                                db.session.add(price_history)
                        except ValueError:
                            pass  # Skip invalid prices
                    
                    imported_count += 1
                    
                    # Commit in batches to avoid memory issues
                    if imported_count % 500 == 0:
                        db.session.commit()
                        
                except Exception as e:
                    error_count += 1
                    print(f"Error importing row: {e} - Row data: {row}")
                    continue
            
            # Final commit
            db.session.commit()
            
            # Create detailed import report
            updated_count = len([item for item in duplicate_items if item.get('action') == 'updated'])
            truly_skipped = duplicate_count - updated_count
            
            if imported_count > 0:
                flash(f'Successfully imported/updated {imported_count} parts!', 'success')
            
            if updated_count > 0:
                flash(f'{updated_count} existing parts were updated with new information', 'info')
            
            if truly_skipped > 0:
                flash(f'{truly_skipped} items skipped (no changes detected)', 'warning')
            
            if error_count > 0:
                flash(f'{error_count} items failed due to missing required fields', 'error')
            
            # Store duplicate report in session for display
            if duplicate_items:
                from flask import session
                session['duplicate_report'] = {
                    'count': duplicate_count,
                    'duplicates': duplicate_items[:20]  # Show first 20 duplicates
                }
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing parts: {str(e)}', 'error')
    
    # Clear any existing duplicate report when page first loads (GET request)
    from flask import session
    session.pop('duplicate_report', None)
    
    # Get current parts count
    parts_count = Parts.query.count()
    
    return render_template('parts/import.html', parts_count=parts_count)

@bp.route('/api/search')
def search_parts():
    """API endpoint for searching parts with filters"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    limit = int(request.args.get('limit', 50))
    
    parts_query = Parts.query
    
    # Apply filters
    if query:
        parts_query = parts_query.filter(
            Parts.description.ilike(f'%{query}%') |
            Parts.part_number.ilike(f'%{query}%') |
            Parts.model.ilike(f'%{query}%')
        )
    
    if category:
        # Join with part_categories table and filter by category name
        parts_query = parts_query.join(PartCategory).filter(PartCategory.name == category)
    
    if manufacturer:
        parts_query = parts_query.filter(Parts.manufacturer == manufacturer)
    
    parts = parts_query.limit(limit).all()
    
    return jsonify([{
        'part_id': part.part_id,
        'part_number': part.part_number,
        'description': part.description,
        'manufacturer': part.manufacturer,
        'category': part.category,
        'price': part.current_price,
        'model': part.model,
        'rating': part.rating
    } for part in parts])

@bp.route('/api/categories', methods=['GET', 'POST'])
@csrf.exempt
def handle_categories():
    """Get all active categories or create a new category"""
    if request.method == 'GET':
        categories = PartCategory.query.filter_by(is_active=True).order_by(PartCategory.name).all()
        return jsonify([{'id': cat.category_id, 'name': cat.name} for cat in categories])
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Category name is required'}), 400
        
        category_name = data['name'].strip()
        if not category_name:
            return jsonify({'error': 'Category name cannot be empty'}), 400
        
        # Check if category already exists
        existing_category = PartCategory.query.filter_by(name=category_name).first()
        if existing_category:
            if existing_category.is_active:
                return jsonify({'error': 'Category already exists'}), 409
            else:
                # Reactivate existing category
                existing_category.is_active = True
                db.session.commit()
                return jsonify({'id': existing_category.category_id, 'name': existing_category.name})
        
        # Create new category
        try:
            new_category = PartCategory(
                name=category_name,
                description=f"User-created category: {category_name}",
                is_active=True
            )
            db.session.add(new_category)
            db.session.commit()
            
            return jsonify({'id': new_category.category_id, 'name': new_category.name}), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to create category: {str(e)}'}), 500

@bp.route('/api/manufacturers')
def get_manufacturers():
    """Get all unique manufacturers"""
    manufacturers = db.session.query(Parts.manufacturer).distinct().filter(Parts.manufacturer != '').all()
    return jsonify([mfr[0] for mfr in manufacturers if mfr[0]])

@bp.route('/price-update', methods=['GET', 'POST'])
@csrf.exempt
def price_update():
    """Update parts pricing from CSV file"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            flash('Please select a CSV or Excel file', 'error')
            return redirect(request.url)
        
        try:
            # Handle different file types
            if file.filename.lower().endswith(('.xlsx', '.xls')):
                # Handle Excel file with proper temp file management
                import tempfile
                import pandas as pd
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                    temp_file_path = temp_file.name
                
                try:
                    file.save(temp_file_path)
                    df = pd.read_excel(temp_file_path)
                finally:
                    # Clean up the temporary file
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                
                if df.empty:
                    flash('Excel file appears to be empty', 'error')
                    return redirect(request.url)
                
                # Convert to CSV-like format for processing
                rows = df.to_dict('records')
                headers = list(df.columns)
                
                # Create a simple reader-like object
                class ExcelReader:
                    def __init__(self, rows, headers):
                        self.fieldnames = headers
                        self.rows = rows
                        self.row_index = 0
                    
                    def __iter__(self):
                        return self
                    
                    def __next__(self):
                        if self.row_index >= len(self.rows):
                            raise StopIteration
                        row = self.rows[self.row_index]
                        self.row_index += 1
                        return {str(k): str(v) if pd.notna(v) else '' for k, v in row.items()}
                
                reader = ExcelReader(rows, headers)
            else:
                # Handle CSV file
                content = file.stream.read()
                
                # Handle BOM and encoding
                if content.startswith(b'\xef\xbb\xbf'):
                    content = content[3:]  # Remove BOM
                
                decoded_content = content.decode('utf-8-sig')
                csv_lines = decoded_content.splitlines()
                
                if len(csv_lines) < 2:  # Header + at least one data row
                    flash('CSV file appears to be empty or invalid', 'error')
                    return redirect(request.url)
                
                # Parse CSV
                reader = csv.DictReader(csv_lines)
            
            # Detect columns - flexible header matching
            headers = reader.fieldnames
            identifier_col = None
            price_col = None
            
            # Find identifier column (includes VFD Excel format support)
            for header in headers:
                header_lower = str(header).lower().strip()
                if any(field in header_lower for field in ['sku', 'part_number', 'part_num', 'partnumber']):
                    identifier_col = header
                    break
                elif any(field in header_lower for field in ['customer part number', 'master_item', 'master_num', 'item_number']):
                    identifier_col = header
                    break
                elif any(field in header_lower for field in ['upc', 'barcode']):
                    identifier_col = header
                    break
            
            # Find price column (includes VFD Excel format support)
            for header in headers:
                header_lower = str(header).lower().strip()
                if any(field in header_lower for field in ['unit price', 'price', 'cost', 'unit_price', 'unitprice']):
                    price_col = header
                    break
            
            if not identifier_col:
                flash('Could not find part identifier column (SKU, Part Number, Customer Part Number, Master Item Number, or UPC)', 'error')
                return redirect(request.url)
            
            if not price_col:
                flash('Could not find price column', 'error')
                return redirect(request.url)
            
            # Process updates
            updated_count = 0
            not_found_count = 0
            unchanged_count = 0
            error_count = 0
            
            file_type = "excel" if file.filename.lower().endswith(('.xlsx', '.xls')) else "csv"
            source = f"{file_type}_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            reason = request.form.get('reason', f'{file_type.upper()} price update')
            
            for row in reader:
                try:
                    identifier = row.get(identifier_col, '').strip()
                    price_str = row.get(price_col, '').strip()
                    
                    if not identifier or not price_str:
                        continue
                    
                    # Clean price string
                    price_str = price_str.replace(',', '').replace('$', '').replace('"', '')
                    
                    try:
                        new_price = float(price_str)
                    except ValueError:
                        error_count += 1
                        continue
                    
                    # Find part by identifier
                    part = Parts.find_by_identifier(identifier)
                    
                    if not part:
                        not_found_count += 1
                        continue
                    
                    # Update price using the new method
                    success, message = part.update_price(
                        new_price=new_price,
                        reason=reason,
                        source=source
                    )
                    
                    if success:
                        updated_count += 1
                    else:
                        unchanged_count += 1
                        
                except Exception as e:
                    error_count += 1
                    print(f"Error processing row {identifier}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Create summary message
            total_processed = updated_count + unchanged_count + not_found_count + error_count
            flash(f'Price update completed: {updated_count} updated, {unchanged_count} unchanged, {not_found_count} not found, {error_count} errors out of {total_processed} rows', 'success')
            
        except Exception as e:
            db.session.rollback()
            file_type = "Excel" if file.filename.lower().endswith(('.xlsx', '.xls')) else "CSV"
            flash(f'Error processing {file_type} file: {str(e)}', 'error')
    
    # Get stats for display
    total_parts = Parts.query.count()
    recent_updates = db.session.query(PartsPriceHistory)\
        .filter(db.or_(
            PartsPriceHistory.source.like('csv_import_%'),
            PartsPriceHistory.source.like('excel_import_%'),
            PartsPriceHistory.source.like('file_import_%')
        ))\
        .order_by(PartsPriceHistory.changed_at.desc())\
        .limit(10).all()
    
    return render_template('parts/price_update.html', 
                         total_parts=total_parts, 
                         recent_updates=recent_updates)

@bp.route('/api/part/<int:part_id>/price-history')
def get_part_price_history(part_id):
    """Get price history for a specific part"""
    part = Parts.query.get_or_404(part_id)
    history = part.get_price_history(limit=20)
    
    # Calculate statistics
    current_price = part.current_price or 0.0
    total_changes = len(history)
    prices = [float(h.new_price) for h in history if h.new_price is not None]
    avg_price = sum(prices) / len(prices) if prices else 0.0
    
    # Determine trend
    trend = 'neutral'
    if len(history) >= 2:
        latest = history[0]
        previous = history[1]
        if latest.new_price is not None and previous.new_price is not None:
            if float(latest.new_price) > float(previous.new_price):
                trend = 'up'
            elif float(latest.new_price) < float(previous.new_price):
                trend = 'down'
    
    # Prepare chart data (last 10 entries)
    chart_history = history[:10][::-1]  # Reverse to show chronologically
    chart_data = {
        'labels': [h.changed_at.strftime('%m/%d/%Y') if h.changed_at else 'N/A' for h in chart_history],
        'datasets': [{
            'label': 'Price History',
            'data': [float(h.new_price) if h.new_price is not None else 0.0 for h in chart_history],
            'borderColor': 'rgb(75, 192, 192)',
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'tension': 0.1
        }]
    }
    
    return jsonify({
        'statistics': {
            'current_price': current_price,
            'total_changes': total_changes,
            'avg_price': avg_price,
            'trend': trend
        },
        'chart_data': chart_data,
        'history': [{
            'history_id': h.history_id,
            'old_price': float(h.old_price) if h.old_price is not None else 0.0,
            'new_price': float(h.new_price) if h.new_price is not None else 0.0,
            'change_amount': (float(h.new_price) if h.new_price is not None else 0.0) - (float(h.old_price) if h.old_price is not None else 0.0),
            'date': h.changed_at.strftime('%m/%d/%Y %H:%M') if h.changed_at else 'N/A',
            'reason': h.changed_reason or 'No reason provided',
            'changed_at': h.changed_at.isoformat() if h.changed_at else None,
            'source': h.source,
            'is_current': h.is_current,
            'effective_date': h.effective_date.isoformat() if h.effective_date else None
        } for h in history]
    })

@bp.route('/clear-duplicate-report', methods=['POST'])
def clear_duplicate_report():
    """Clear the duplicate report from session"""
    from flask import session
    session.pop('duplicate_report', None)
    return jsonify({'status': 'success'})

@bp.route('/categories')
def manage_categories():
    """Manage part categories with Excel-like interface"""
    categories = PartCategory.query.order_by(PartCategory.name).all()
    return render_template('parts/categories.html', categories=categories)

@bp.route('/api/categories/<int:category_id>', methods=['PUT', 'DELETE'])
def manage_category(category_id):
    """Update or delete a category"""
    category = PartCategory.query.get_or_404(category_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        if 'name' in data:
            # Check if name already exists
            existing = PartCategory.query.filter(
                PartCategory.name == data['name'],
                PartCategory.category_id != category_id
            ).first()
            if existing:
                return jsonify({'error': 'Category name already exists'}), 400
            
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        
        db.session.commit()
        return jsonify({
            'category_id': category.category_id,
            'name': category.name,
            'description': category.description
        })
    
    elif request.method == 'DELETE':
        # Check if category is in use
        parts_using_category = Parts.query.filter_by(category_id=category_id).count()
        if parts_using_category > 0:
            return jsonify({'error': f'Cannot delete category. {parts_using_category} parts are using this category.'}), 400
        
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})

@bp.route('/api/categories/new', methods=['POST'])
@csrf.exempt
def create_category():
    """Create a new category"""
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'error': 'Category name is required'}), 400
    
    # Check if name already exists
    existing = PartCategory.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Category name already exists'}), 400
    
    category = PartCategory(name=name, description=description)
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'category_id': category.category_id,
        'name': category.name,
        'description': category.description
    })
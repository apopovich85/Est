from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Parts, PartsPriceHistory
from app import db, csrf
import csv
import os
from datetime import datetime
from decimal import Decimal

bp = Blueprint('parts', __name__)

@bp.route('/import', methods=['GET', 'POST'])
@csrf.exempt
def import_parts():
    """Import parts from CSV file"""
    if request.method == 'POST':
        try:
            csv_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'partsdb.csv')
            
            if not os.path.exists(csv_file_path):
                flash('CSV file not found!', 'error')
                return redirect(url_for('parts.import_parts'))
            
            # Clear existing parts
            if request.form.get('clear_existing'):
                Parts.query.delete()
                db.session.commit()
            
            imported_count = 0
            error_count = 0
            
            with open(csv_file_path, 'r', encoding='utf-8-sig', newline='') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    try:
                        # Clean price field (remove commas and quotes)
                        price_str = row.get('price', '0').replace(',', '').replace('"', '')
                        
                        # Parse effective date
                        effective_date = None
                        if row.get('effective_date'):
                            try:
                                effective_date = datetime.strptime(row['effective_date'], '%m/%d/%Y').date()
                            except ValueError:
                                pass  # Skip invalid dates
                        
                        part = Parts(
                            category=row.get('Category', '').strip(),
                            model=row.get('Model', '').strip() or None,
                            rating=row.get('Rating', '').strip() or None,
                            master_item_number=row.get('master_item_number', '').strip() or None,
                            manufacturer=row.get('manu', '').strip(),
                            part_number=row.get('part_number', '').strip(),
                            upc=row.get('upc', '').strip() or None,
                            description=row.get('Description', '').strip(),
                            price=float(price_str) if price_str else None,
                            vendor=row.get('vendor', '').strip() or None,
                            effective_date=effective_date
                        )
                        
                        db.session.add(part)
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
                
            flash(f'Successfully imported {imported_count} parts with {error_count} errors!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing parts: {str(e)}', 'error')
    
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
        parts_query = parts_query.filter(Parts.category == category)
    
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

@bp.route('/api/categories')
def get_categories():
    """Get all unique categories"""
    categories = db.session.query(Parts.category).distinct().filter(Parts.category != '').all()
    return jsonify([cat[0] for cat in categories if cat[0]])

@bp.route('/api/manufacturers')
def get_manufacturers():
    """Get all unique manufacturers"""
    manufacturers = db.session.query(Parts.manufacturer).distinct().filter(Parts.manufacturer != '').all()
    return jsonify([mfr[0] for mfr in manufacturers if mfr[0]])

@bp.route('/price-update', methods=['GET', 'POST'])
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
        
        if not file.filename.lower().endswith('.csv'):
            flash('Please select a CSV file', 'error')
            return redirect(request.url)
        
        try:
            # Read CSV content
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
            
            # Find identifier column (part_number, master_item_number, or upc)
            for header in headers:
                header_lower = header.lower().strip()
                if any(field in header_lower for field in ['part_number', 'part_num', 'partnumber']):
                    identifier_col = header
                    break
                elif any(field in header_lower for field in ['master_item', 'master_num', 'item_number']):
                    identifier_col = header
                    break
                elif any(field in header_lower for field in ['upc', 'barcode']):
                    identifier_col = header
                    break
            
            # Find price column
            for header in headers:
                header_lower = header.lower().strip()
                if any(field in header_lower for field in ['price', 'cost', 'unit_price', 'unitprice']):
                    price_col = header
                    break
            
            if not identifier_col:
                flash('Could not find part identifier column (part_number, master_item_number, or upc)', 'error')
                return redirect(request.url)
            
            if not price_col:
                flash('Could not find price column', 'error')
                return redirect(request.url)
            
            # Process updates
            updated_count = 0
            not_found_count = 0
            unchanged_count = 0
            error_count = 0
            
            source = f"csv_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            reason = request.form.get('reason', 'CSV price update')
            
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
            flash(f'Error processing CSV file: {str(e)}', 'error')
    
    # Get stats for display
    total_parts = Parts.query.count()
    recent_updates = db.session.query(PartsPriceHistory)\
        .filter(PartsPriceHistory.source.like('csv_import_%'))\
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
    
    return jsonify([{
        'history_id': h.history_id,
        'old_price': float(h.old_price) if h.old_price else None,
        'new_price': float(h.new_price) if h.new_price else None,
        'changed_at': h.changed_at.isoformat() if h.changed_at else None,
        'changed_reason': h.changed_reason,
        'source': h.source,
        'is_current': h.is_current,
        'effective_date': h.effective_date.isoformat() if h.effective_date else None
    } for h in history])
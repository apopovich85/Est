from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db
from datetime import datetime
import sqlite3

bp = Blueprint('labor_rates', __name__)

class LaborRates:
    """Model for labor rates configuration"""
    
    @staticmethod
    def get_current_rates():
        """Get the current active labor rates"""
        conn = sqlite3.connect('estimates.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT engineering_rate, panel_shop_rate, machine_assembly_rate, effective_date, notes
            FROM labor_rates 
            WHERE is_current = 1 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'engineering_rate': float(result[0]),
                'panel_shop_rate': float(result[1]), 
                'machine_assembly_rate': float(result[2]),
                'effective_date': result[3],
                'notes': result[4]
            }
        
        # Fallback to default rates
        return {
            'engineering_rate': 145.00,
            'panel_shop_rate': 125.00,
            'machine_assembly_rate': 125.00,
            'effective_date': None,
            'notes': 'Default rates'
        }
    
    @staticmethod
    def get_rate_history():
        """Get all rate history ordered by date"""
        conn = sqlite3.connect('estimates.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rate_id, engineering_rate, panel_shop_rate, machine_assembly_rate, 
                   effective_date, is_current, notes, created_by, created_at
            FROM labor_rates 
            ORDER BY created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'rate_id': row[0],
            'engineering_rate': float(row[1]),
            'panel_shop_rate': float(row[2]),
            'machine_assembly_rate': float(row[3]),
            'effective_date': row[4],
            'is_current': bool(row[5]),
            'notes': row[6],
            'created_by': row[7],
            'created_at': row[8]
        } for row in results]
    
    @staticmethod
    def update_rates(engineering_rate, panel_shop_rate, machine_assembly_rate, notes='', created_by=''):
        """Update labor rates and mark as current"""
        conn = sqlite3.connect('estimates.db')
        cursor = conn.cursor()
        
        # Mark all current rates as not current
        cursor.execute('UPDATE labor_rates SET is_current = 0')
        
        # Insert new rates
        cursor.execute('''
            INSERT INTO labor_rates 
            (engineering_rate, panel_shop_rate, machine_assembly_rate, effective_date, 
             is_current, notes, created_by)
            VALUES (?, ?, ?, date('now'), 1, ?, ?)
        ''', (engineering_rate, panel_shop_rate, machine_assembly_rate, notes, created_by))
        
        conn.commit()
        conn.close()

@bp.route('/')
def labor_rates_config():
    """Labor rates configuration page"""
    current_rates = LaborRates.get_current_rates()
    rate_history = LaborRates.get_rate_history()
    
    return render_template('labor_rates/config.html', 
                         current_rates=current_rates, 
                         rate_history=rate_history)

@bp.route('/update', methods=['POST'])
def update_rates():
    """Update labor rates"""
    try:
        engineering_rate = float(request.form['engineering_rate'])
        panel_shop_rate = float(request.form['panel_shop_rate'])
        machine_assembly_rate = float(request.form['machine_assembly_rate'])
        notes = request.form.get('notes', '')
        created_by = request.form.get('created_by', 'User')
        
        LaborRates.update_rates(engineering_rate, panel_shop_rate, machine_assembly_rate, notes, created_by)
        
        flash('Labor rates updated successfully!', 'success')
        
    except ValueError as e:
        flash('Invalid rate values. Please enter valid numbers.', 'error')
    except Exception as e:
        flash(f'Error updating rates: {str(e)}', 'error')
    
    return redirect(url_for('labor_rates.labor_rates_config'))

@bp.route('/api/current')
def api_current_rates():
    """API endpoint to get current labor rates"""
    return jsonify(LaborRates.get_current_rates())
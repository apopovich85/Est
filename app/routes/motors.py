from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Motor, Project, VFDType, NECAmpTable, Parts, TechData
from sqlalchemy import and_, cast, Float

bp = Blueprint('motors', __name__, url_prefix='/motors')

@bp.route('/project/<int:project_id>')
def list_motors(project_id):
    """List all motors and loads for a project"""
    project = Project.query.get_or_404(project_id)
    motors = Motor.query.filter_by(project_id=project_id).order_by(Motor.sort_order, Motor.motor_name).all()
    return render_template('motors/list.html', project=project, motors=motors)

@bp.route('/project/<int:project_id>/create')
def create_motor_form(project_id):
    """Show create motor/load form"""
    project = Project.query.get_or_404(project_id)
    vfd_types = VFDType.get_active_types()
    
    # Voltage options
    voltage_options = [115, 200, 208, 230, 460, 575, 2300]
    
    return render_template('motors/create.html', 
                         project=project, 
                         vfd_types=vfd_types,
                         voltage_options=voltage_options)

@bp.route('/project/<int:project_id>/create', methods=['POST'])
def create_motor(project_id):
    """Create a new motor"""
    project = Project.query.get_or_404(project_id)
    
    try:
        load_type = request.form.get('load_type', 'motor')
        
        # Get voltage from appropriate field based on load type
        if load_type == 'load':
            voltage = float(request.form['voltage_load'])
        else:
            voltage = float(request.form['voltage'])
            
        motor = Motor(
            project_id=project_id,
            load_type=load_type,
            motor_name=request.form['motor_name'],
            location=request.form.get('location', ''),
            voltage=voltage,
            qty=int(request.form['qty']),
            continuous_load=bool(request.form.get('continuous_load')),
            additional_notes=request.form.get('additional_notes', ''),
            nec_amps_override=bool(request.form.get('nec_amps_override')),
            manual_amps=float(request.form['manual_amps']) if request.form.get('manual_amps') else None
        )
        
        # Motor-specific fields
        if load_type == 'motor':
            motor.hp = float(request.form['hp']) if request.form.get('hp') else None
            motor.encl_type = request.form.get('encl_type', '')
            motor.frame = request.form.get('frame', '')
            motor.speed_range = request.form.get('speed_range', '')
            motor.overload_percentage = float(request.form.get('overload_percentage', 1.15))
            motor.vfd_type_id = int(request.form['vfd_type_id']) if request.form.get('vfd_type_id') else None
            motor.vfd_override = bool(request.form.get('vfd_override'))
            motor.selected_vfd_part_id = int(request.form['selected_vfd_part_id']) if request.form.get('selected_vfd_part_id') else None
        else:
            # Load-specific fields
            motor.power_rating = float(request.form['power_rating']) if request.form.get('power_rating') else None
            motor.power_unit = request.form.get('power_unit', 'kVA')
            motor.phase_config = request.form.get('phase_config', 'three')
        
        db.session.add(motor)
        db.session.commit()
        flash('Motor added successfully!', 'success')
        return redirect(url_for('motors.list_motors', project_id=project_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating motor: {str(e)}', 'error')
        return redirect(url_for('motors.create_motor_form', project_id=project_id))

@bp.route('/edit/<int:motor_id>')
def edit_motor_form(motor_id):
    """Show edit motor form"""
    motor = Motor.query.get_or_404(motor_id)
    project = motor.project
    vfd_types = VFDType.get_active_types()
    
    # Voltage options
    voltage_options = [115, 200, 208, 230, 460, 575, 2300]
    
    # Get VFD options for override dropdown
    vfd_options = motor.get_vfd_options() if motor.vfd_type_id else []
    
    return render_template('motors/edit.html', 
                         motor=motor,
                         project=project, 
                         vfd_types=vfd_types,
                         voltage_options=voltage_options,
                         vfd_options=vfd_options)

@bp.route('/edit/<int:motor_id>', methods=['POST'])
def edit_motor(motor_id):
    """Update a motor"""
    motor = Motor.query.get_or_404(motor_id)
    
    try:
        load_type = request.form.get('load_type', 'motor')
        
        # Get voltage from appropriate field based on load type
        if load_type == 'load':
            voltage = float(request.form['voltage_load'])
        else:
            voltage = float(request.form['voltage'])
            
        # Common fields
        motor.load_type = load_type
        motor.motor_name = request.form['motor_name']
        motor.location = request.form.get('location', '')
        motor.voltage = voltage
        motor.qty = int(request.form['qty'])
        motor.continuous_load = bool(request.form.get('continuous_load'))
        motor.additional_notes = request.form.get('additional_notes', '')
        motor.nec_amps_override = bool(request.form.get('nec_amps_override'))
        motor.manual_amps = float(request.form['manual_amps']) if request.form.get('manual_amps') else None
        
        # Motor-specific fields
        if load_type == 'motor':
            motor.hp = float(request.form['hp']) if request.form.get('hp') else None
            motor.encl_type = request.form.get('encl_type', '')
            motor.frame = request.form.get('frame', '')
            motor.speed_range = request.form.get('speed_range', '')
            motor.overload_percentage = float(request.form.get('overload_percentage', 1.15))
            motor.vfd_type_id = int(request.form['vfd_type_id']) if request.form.get('vfd_type_id') else None
            motor.vfd_override = bool(request.form.get('vfd_override'))
            motor.selected_vfd_part_id = int(request.form['selected_vfd_part_id']) if request.form.get('selected_vfd_part_id') else None
            # Clear load fields
            motor.power_rating = None
            motor.power_unit = 'kVA'
            motor.phase_config = 'three'
        else:
            # Load-specific fields
            motor.power_rating = float(request.form['power_rating']) if request.form.get('power_rating') else None
            motor.power_unit = request.form.get('power_unit', 'kVA')
            motor.phase_config = request.form.get('phase_config', 'three')
            # Clear motor fields
            motor.hp = None
            motor.encl_type = None
            motor.frame = None
            motor.speed_range = None
            motor.overload_percentage = None
            motor.vfd_type_id = None
            motor.vfd_override = False
            motor.selected_vfd_part_id = None
        
        db.session.commit()
        flash('Motor updated successfully!', 'success')
        return redirect(url_for('motors.list_motors', project_id=motor.project_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating motor: {str(e)}', 'error')
        return redirect(url_for('motors.edit_motor_form', motor_id=motor_id))

@bp.route('/delete/<int:motor_id>', methods=['POST'])
def delete_motor(motor_id):
    """Delete a motor"""
    motor = Motor.query.get_or_404(motor_id)
    project_id = motor.project_id
    
    try:
        db.session.delete(motor)
        db.session.commit()
        flash('Motor deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting motor: {str(e)}', 'error')
    
    return redirect(url_for('motors.list_motors', project_id=project_id))

@bp.route('/api/vfd_options/<int:motor_id>')
def get_vfd_options(motor_id):
    """Get VFD options for a motor via API"""
    motor = Motor.query.get_or_404(motor_id)
    vfd_options = motor.get_vfd_options()
    
    options = []
    for vfd in vfd_options:
        options.append({
            'part_id': vfd.part_id,
            'part_number': vfd.part_number,
            'description': vfd.description,
            'rating': vfd.rating,
            'current_price': vfd.current_price
        })
    
    return jsonify(options)

@bp.route('/api/vfd_options_by_type')
def get_vfd_options_by_type():
    """Get VFD options by type and required current via API"""
    vfd_type_id = request.args.get('vfd_type_id', type=int)
    required_current = request.args.get('required_current', type=float)
    
    if not vfd_type_id or not required_current:
        return jsonify([])
    
    vfd_type = VFDType.query.get(vfd_type_id)
    if not vfd_type:
        return jsonify([])
    
    # Find VFDs that match the type and have sufficient rating
    vfd_options = db.session.query(Parts)\
        .filter(and_(
            Parts.description.contains(vfd_type.type_name),
            cast(Parts.rating, Float) >= required_current
        ))\
        .order_by(cast(Parts.rating, Float).asc())\
        .all()
    
    options = []
    for vfd in vfd_options:
        options.append({
            'part_id': vfd.part_id,
            'part_number': vfd.part_number,
            'description': vfd.description,
            'rating': vfd.rating,
            'current_price': vfd.current_price
        })
    
    return jsonify(options)

@bp.route('/api/motor_amps')
def get_motor_amps():
    """Get motor amps from NEC table via API"""
    hp = request.args.get('hp', type=float)
    voltage = request.args.get('voltage', type=float)
    
    if not hp or not voltage:
        return jsonify({'amps': None})
    
    amps = NECAmpTable.get_motor_amps(hp, voltage)
    return jsonify({'amps': amps})

@bp.route('/api/motor_calculations/<int:motor_id>')
def get_motor_calculations(motor_id):
    """Get all calculated values for a motor via API"""
    motor = Motor.query.get_or_404(motor_id)
    
    calculations = {
        'motor_amps': motor.motor_amps,
        'total_amps': motor.total_amps,
        'drive_required_current': motor.drive_required_current,
        'recommended_vfd': {
            'part_number': motor.recommended_vfd.part_number if motor.recommended_vfd else None,
            'description': motor.recommended_vfd.description if motor.recommended_vfd else None,
            'rating': motor.recommended_vfd.rating if motor.recommended_vfd else None,
        } if motor.recommended_vfd else None,
        'vfd_input_current': motor.vfd_input_current,
        'total_vfd_input_current': motor.total_vfd_input_current,
        'vfd_heat_loss': motor.vfd_heat_loss,
        'vfd_width': motor.vfd_width,
        'total_width': motor.total_width
    }
    
    return jsonify(calculations)
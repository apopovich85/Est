from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models import Motor, Project, VFDType, NECAmpTable, Parts, TechData, MotorRevision
from sqlalchemy import and_, cast, Float
import json

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

@bp.route('/edit/<int:motor_id>/detect_changes', methods=['POST'])
def detect_motor_changes(motor_id):
    """Detect changes and suggest revision type"""
    motor = Motor.query.get_or_404(motor_id)

    try:
        # Build new_data dictionary from form
        load_type = request.form.get('load_type', 'motor')

        if load_type == 'load':
            voltage = float(request.form['voltage_load']) if request.form.get('voltage_load') else None
        else:
            voltage = float(request.form['voltage']) if request.form.get('voltage') else None

        new_data = {
            'load_type': load_type,
            'motor_name': request.form.get('motor_name', ''),
            'location': request.form.get('location', ''),
            'voltage': voltage,
            'qty': int(request.form['qty']) if request.form.get('qty') else 1,
            'continuous_load': bool(request.form.get('continuous_load')),
            'additional_notes': request.form.get('additional_notes', ''),
            'nec_amps_override': bool(request.form.get('nec_amps_override')),
            'manual_amps': float(request.form['manual_amps']) if request.form.get('manual_amps') else None
        }

        # Motor-specific fields
        if load_type == 'motor':
            new_data.update({
                'hp': float(request.form['hp']) if request.form.get('hp') else None,
                'encl_type': request.form.get('encl_type', ''),
                'frame': request.form.get('frame', ''),
                'speed_range': request.form.get('speed_range', ''),
                'overload_percentage': float(request.form.get('overload_percentage', 1.15)) if request.form.get('overload_percentage') else 1.15,
                'vfd_type_id': int(request.form['vfd_type_id']) if request.form.get('vfd_type_id') else None,
                'vfd_override': bool(request.form.get('vfd_override')),
                'selected_vfd_part_id': int(request.form['selected_vfd_part_id']) if request.form.get('selected_vfd_part_id') else None,
                'power_rating': None,
                'power_unit': 'kVA',
                'phase_config': 'three'
            })
        else:
            # Load-specific fields
            new_data.update({
                'power_rating': float(request.form['power_rating']) if request.form.get('power_rating') else None,
                'power_unit': request.form.get('power_unit', 'kVA'),
                'phase_config': request.form.get('phase_config', 'three'),
                'hp': None,
                'encl_type': None,
                'frame': None,
                'speed_range': None,
                'overload_percentage': None,
                'vfd_type_id': None,
                'vfd_override': False,
                'selected_vfd_part_id': None
            })

        # Detect changes
        changed_fields, suggested_type = motor.detect_changes(new_data)

        return jsonify({
            'success': True,
            'changed_fields': changed_fields,
            'suggested_revision_type': suggested_type,
            'current_revision': motor.revision_number,
            'next_major': motor.increment_revision('major'),
            'next_minor': motor.increment_revision('minor')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/edit/<int:motor_id>', methods=['POST'])
def edit_motor(motor_id):
    """Update a motor with revision control"""
    motor = Motor.query.get_or_404(motor_id)

    try:
        # Get revision type from form (user's choice)
        revision_type = request.form.get('revision_type', 'minor')
        change_description = request.form.get('change_description', '')

        # Build new_data for change detection
        load_type = request.form.get('load_type', 'motor')

        if load_type == 'load':
            voltage = float(request.form['voltage_load']) if request.form.get('voltage_load') else None
        else:
            voltage = float(request.form['voltage']) if request.form.get('voltage') else None

        new_data = {
            'load_type': load_type,
            'motor_name': request.form.get('motor_name', ''),
            'location': request.form.get('location', ''),
            'voltage': voltage,
            'qty': int(request.form['qty']) if request.form.get('qty') else 1,
            'continuous_load': bool(request.form.get('continuous_load')),
            'additional_notes': request.form.get('additional_notes', ''),
            'nec_amps_override': bool(request.form.get('nec_amps_override')),
            'manual_amps': float(request.form['manual_amps']) if request.form.get('manual_amps') else None
        }

        # Motor-specific or load-specific fields
        if load_type == 'motor':
            new_data.update({
                'hp': float(request.form['hp']) if request.form.get('hp') else None,
                'encl_type': request.form.get('encl_type', ''),
                'frame': request.form.get('frame', ''),
                'speed_range': request.form.get('speed_range', ''),
                'overload_percentage': float(request.form.get('overload_percentage', 1.15)) if request.form.get('overload_percentage') else 1.15,
                'vfd_type_id': int(request.form['vfd_type_id']) if request.form.get('vfd_type_id') else None,
                'vfd_override': bool(request.form.get('vfd_override')),
                'selected_vfd_part_id': int(request.form['selected_vfd_part_id']) if request.form.get('selected_vfd_part_id') else None
            })
        else:
            new_data.update({
                'power_rating': float(request.form['power_rating']) if request.form.get('power_rating') else None,
                'power_unit': request.form.get('power_unit', 'kVA'),
                'phase_config': request.form.get('phase_config', 'three')
            })

        # Detect changes for revision history
        changed_fields, _ = motor.detect_changes(new_data)

        # Create revision snapshot BEFORE making changes
        if changed_fields:  # Only create revision if something actually changed
            motor.create_revision(
                changed_by='User',
                change_description=change_description,
                revision_type=revision_type,
                fields_changed=changed_fields
            )

        # Update motor fields
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

        # Update revision number based on type
        if changed_fields:
            motor.revision_number = motor.increment_revision(revision_type)
            motor.revision_type = revision_type

        db.session.commit()

        revision_msg = f" (Rev. {motor.revision_number})" if changed_fields else " (no changes)"
        flash(f'Motor updated successfully{revision_msg}!', 'success')
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

@bp.route('/<int:motor_id>/revisions')
def view_revisions(motor_id):
    """View revision history for a motor"""
    motor = Motor.query.get_or_404(motor_id)
    revisions = MotorRevision.query.filter_by(motor_id=motor_id).order_by(MotorRevision.created_at.desc()).all()

    revision_list = []
    for rev in revisions:
        # Parse fields_changed if it exists
        fields_changed = None
        if rev.fields_changed:
            try:
                fields_changed = eval(rev.fields_changed)  # Safe here since we control the data
            except:
                fields_changed = None

        revision_list.append({
            'revision_number': rev.revision_number,
            'revision_type': rev.revision_type,
            'motor_name': rev.motor_name,
            'hp': float(rev.hp) if rev.hp else None,
            'voltage': float(rev.voltage),
            'qty': rev.qty,
            'changed_by': rev.changed_by,
            'change_description': rev.change_description,
            'fields_changed': fields_changed,
            'created_at': rev.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({
        'success': True,
        'current_revision': motor.revision_number,
        'revisions': revision_list
    })

@bp.route('/<int:motor_id>/compare/<revision_a>/<revision_b>')
def compare_revisions(motor_id, revision_a, revision_b):
    """Compare two revisions"""
    motor = Motor.query.get_or_404(motor_id)

    # Get current state if revision_a is 'current'
    if revision_a == 'current':
        rev_a_data = {
            'revision_number': motor.revision_number,
            'motor_name': motor.motor_name,
            'hp': float(motor.hp) if motor.hp else None,
            'voltage': float(motor.voltage),
            'qty': motor.qty,
            'location': motor.location,
            'load_type': motor.load_type,
            'power_rating': float(motor.power_rating) if motor.power_rating else None,
            'vfd_type_id': motor.vfd_type_id
        }
    else:
        rev_a = MotorRevision.query.filter_by(motor_id=motor_id, revision_number=revision_a).first()
        if not rev_a:
            return jsonify({'success': False, 'message': 'Revision A not found'}), 404
        rev_a_data = {
            'revision_number': rev_a.revision_number,
            'motor_name': rev_a.motor_name,
            'hp': float(rev_a.hp) if rev_a.hp else None,
            'voltage': float(rev_a.voltage),
            'qty': rev_a.qty,
            'location': rev_a.location,
            'load_type': rev_a.load_type,
            'power_rating': float(rev_a.power_rating) if rev_a.power_rating else None,
            'vfd_type_id': rev_a.vfd_type_id
        }

    # Get revision B
    rev_b = MotorRevision.query.filter_by(motor_id=motor_id, revision_number=revision_b).first()
    if not rev_b:
        return jsonify({'success': False, 'message': 'Revision B not found'}), 404

    rev_b_data = {
        'revision_number': rev_b.revision_number,
        'motor_name': rev_b.motor_name,
        'hp': float(rev_b.hp) if rev_b.hp else None,
        'voltage': float(rev_b.voltage),
        'qty': rev_b.qty,
        'location': rev_b.location,
        'load_type': rev_b.load_type,
        'power_rating': float(rev_b.power_rating) if rev_b.power_rating else None,
        'vfd_type_id': rev_b.vfd_type_id
    }

    # Find differences
    differences = {}
    for key in rev_a_data.keys():
        if key == 'revision_number':
            continue
        if rev_a_data.get(key) != rev_b_data.get(key):
            differences[key] = {
                'revision_a': rev_a_data.get(key),
                'revision_b': rev_b_data.get(key)
            }

    return jsonify({
        'success': True,
        'revision_a': rev_a_data,
        'revision_b': rev_b_data,
        'differences': differences
    })

@bp.route('/<int:motor_id>/revert/<revision_number>', methods=['POST'])
def revert_to_revision(motor_id, revision_number):
    """Revert motor to a specific revision"""
    motor = Motor.query.get_or_404(motor_id)

    try:
        motor.revert_to_revision(revision_number)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Reverted to revision {revision_number}'
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error reverting: {str(e)}'
        }), 500

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

@bp.route('/project/<int:project_id>/copy')
def copy_motors_form(project_id):
    """Show form to copy motors from other projects"""
    project = Project.query.get_or_404(project_id)
    
    # Get all other projects that have motors
    other_projects = db.session.query(Project)\
        .join(Motor)\
        .filter(Project.project_id != project_id)\
        .distinct()\
        .order_by(Project.project_name)\
        .all()
    
    return render_template('motors/copy.html', 
                         project=project, 
                         other_projects=other_projects)

@bp.route('/project/<int:project_id>/copy', methods=['POST'])
def copy_motors(project_id):
    """Copy selected motors from another project"""
    project = Project.query.get_or_404(project_id)
    source_project_id = request.form.get('source_project_id', type=int)
    selected_motor_ids = request.form.getlist('motor_ids', type=int)
    
    if not source_project_id or not selected_motor_ids:
        flash('Please select a source project and at least one motor to copy.', 'error')
        return redirect(url_for('motors.copy_motors_form', project_id=project_id))
    
    try:
        source_motors = Motor.query.filter(
            Motor.project_id == source_project_id,
            Motor.motor_id.in_(selected_motor_ids)
        ).all()
        
        copied_count = 0
        for source_motor in source_motors:
            # Create new motor with same properties but different project_id
            new_motor = Motor(
                project_id=project_id,
                load_type=source_motor.load_type,
                motor_name=source_motor.motor_name,  # Keep original title
                location=source_motor.location,
                encl_type=source_motor.encl_type,
                frame=source_motor.frame,
                additional_notes=source_motor.additional_notes,
                hp=source_motor.hp,
                speed_range=source_motor.speed_range,
                voltage=source_motor.voltage,
                qty=source_motor.qty,
                overload_percentage=source_motor.overload_percentage,
                continuous_load=source_motor.continuous_load,
                vfd_type_id=source_motor.vfd_type_id,
                power_rating=source_motor.power_rating,
                power_unit=source_motor.power_unit,
                phase_config=source_motor.phase_config,
                nec_amps_override=source_motor.nec_amps_override,
                manual_amps=source_motor.manual_amps,
                vfd_override=source_motor.vfd_override,
                selected_vfd_part_id=source_motor.selected_vfd_part_id,
                sort_order=source_motor.sort_order
            )
            
            db.session.add(new_motor)
            copied_count += 1
        
        db.session.commit()
        flash(f'Successfully copied {copied_count} motor(s) to this project!', 'success')
        return redirect(url_for('motors.list_motors', project_id=project_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error copying motors: {str(e)}', 'error')
        return redirect(url_for('motors.copy_motors_form', project_id=project_id))

@bp.route('/api/project_motors/<int:project_id>')
def get_project_motors(project_id):
    """Get motors for a specific project via API"""
    motors = Motor.query.filter_by(project_id=project_id)\
        .order_by(Motor.sort_order, Motor.motor_name)\
        .all()
    
    motor_list = []
    for motor in motors:
        motor_list.append({
            'motor_id': motor.motor_id,
            'motor_name': motor.motor_name,
            'load_type': motor.load_type,
            'location': motor.location,
            'hp': float(motor.hp) if motor.hp else None,
            'voltage': float(motor.voltage),
            'qty': motor.qty,
            'motor_amps': motor.motor_amps,
            'total_amps': motor.total_amps
        })
    
    return jsonify(motor_list)
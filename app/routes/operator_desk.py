from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import Project, Estimate, Assembly, Parts, AssemblyPart, EstimateComponent
from app import db, csrf
import uuid
from datetime import datetime, date
import sqlite3
import math

bp = Blueprint('operator_desk', __name__)

# Component to I/O mapping
DIGITAL_IO_MAP = {
    'momentary_pb': {
        'standard_inputs': 1,
        'safety_inputs': 0,
        'outputs': 0
    },
    'illuminated_pb': {
        'standard_inputs': 1,      # Button press feedback
        'safety_inputs': 0,
        'outputs': 1               # LED control
    },
    'pilot_light': {
        'standard_inputs': 0,
        'safety_inputs': 0,
        'outputs': 1               # Light control
    },
    'estop': {
        'standard_inputs': 0,
        'safety_inputs': 2,        # 2 safety inputs per E-stop
        'outputs': 1               # Red fault light
    },
    'selector_2pos': {
        'standard_inputs': 1,      # Position feedback
        'safety_inputs': 0,
        'outputs': 0
    },
    'selector_3pos': {
        'standard_inputs': 2,      # Position feedback (2 inputs)
        'safety_inputs': 0,
        'outputs': 0
    },
    'trap_key': {
        'standard_inputs': 1,      # Position feedback
        'safety_inputs': 0,
        'outputs': 0
    }
}

# I/O Module specifications
IO_MODULE_POWER = {
    '1734-AENTR': {'backplane_current_ma': 200},
    '1734-IB8': {'backplane_current_ma': 150},
    '1734-IB8S': {'backplane_current_ma': 180},
    '1734-OB8': {'backplane_current_ma': 160},
    '1734-EP24DC': {'backplane_current_ma': 50},
    '1734-EP': {'backplane_current_ma': 5},
}

BACKPLANE_LIMITS = {
    'standard_backplane_max_ma': 1000,
    'safety_margin_percent': 10
}

@bp.route('/wizard')
def wizard():
    """Main operator desk configuration wizard"""
    projects = Project.query.all()
    return render_template('operator_desk/wizard.html', projects=projects)

@bp.route('/api/calculate-io', methods=['POST'])
def calculate_io():
    """Calculate I/O requirements from control selections"""
    try:
        controls = request.json.get('controls', {})
        
        # Calculate raw I/O requirements
        total_standard_inputs = 0
        total_safety_inputs = 0
        total_outputs = 0
        
        for control_type, qty in controls.items():
            if control_type in DIGITAL_IO_MAP:
                io_map = DIGITAL_IO_MAP[control_type]
                total_standard_inputs += io_map['standard_inputs'] * qty
                total_safety_inputs += io_map['safety_inputs'] * qty
                total_outputs += io_map['outputs'] * qty
        
        # Add 20% spare capacity (rounded up)
        required_standard_inputs = math.ceil(total_standard_inputs * 1.2)
        required_safety_inputs = math.ceil(total_safety_inputs * 1.2)
        required_outputs = math.ceil(total_outputs * 1.2)
        
        # Calculate modules needed
        modules = []
        
        # Standard input modules
        if required_standard_inputs > 0:
            input_modules = math.ceil(required_standard_inputs / 8)
            for i in range(input_modules):
                modules.append({
                    'part_number': '1734-IB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_standard_inputs - (i * 8)),
                    'points_available': 8,
                    'module_type': 'standard_input'
                })
        
        # Safety input modules
        if required_safety_inputs > 0:
            safety_modules = math.ceil(required_safety_inputs / 8)
            for i in range(safety_modules):
                modules.append({
                    'part_number': '1734-IB8S',
                    'wiring_bases_needed': 2,
                    'points_used': min(8, required_safety_inputs - (i * 8)),
                    'points_available': 8,
                    'module_type': 'safety_input'
                })
        
        # Output modules
        if required_outputs > 0:
            output_modules = math.ceil(required_outputs / 8)
            for i in range(output_modules):
                modules.append({
                    'part_number': '1734-OB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_outputs - (i * 8)),
                    'points_available': 8,
                    'module_type': 'output'
                })
        
        # Calculate power requirements
        total_current = 0
        total_current += IO_MODULE_POWER['1734-AENTR']['backplane_current_ma']  # Always included
        total_current += IO_MODULE_POWER['1734-EP']['backplane_current_ma']     # Always included
        
        for module in modules:
            total_current += IO_MODULE_POWER[module['part_number']]['backplane_current_ma']
        
        # Check if expansion power needed
        max_allowed = BACKPLANE_LIMITS['standard_backplane_max_ma'] * (1 - BACKPLANE_LIMITS['safety_margin_percent'] / 100)
        expansion_power_needed = total_current > max_allowed
        
        if expansion_power_needed:
            modules.append({
                'part_number': '1734-EP24DC',
                'wiring_bases_needed': 0,
                'points_used': 0,
                'points_available': 0,
                'module_type': 'power_supply'
            })
            total_current += IO_MODULE_POWER['1734-EP24DC']['backplane_current_ma']
        
        # Calculate totals for display
        std_input_total = sum(8 for m in modules if m['module_type'] == 'standard_input')
        safety_input_total = sum(8 for m in modules if m['module_type'] == 'safety_input')
        output_total = sum(8 for m in modules if m['module_type'] == 'output')
        
        # Calculate spare percentages
        std_spare = std_input_total - total_standard_inputs if std_input_total > 0 else 0
        safety_spare = safety_input_total - total_safety_inputs if safety_input_total > 0 else 0
        output_spare = output_total - total_outputs if output_total > 0 else 0
        
        std_spare_percent = (std_spare / std_input_total * 100) if std_input_total > 0 else 0
        safety_spare_percent = (safety_spare / safety_input_total * 100) if safety_input_total > 0 else 0
        output_spare_percent = (output_spare / output_total * 100) if output_total > 0 else 0
        
        return jsonify({
            'success': True,
            'io_analysis': {
                'standard_inputs': {
                    'used': total_standard_inputs,
                    'total': std_input_total,
                    'spare': std_spare,
                    'spare_percent': round(std_spare_percent, 1)
                },
                'safety_inputs': {
                    'used': total_safety_inputs,
                    'total': safety_input_total,
                    'spare': safety_spare,
                    'spare_percent': round(safety_spare_percent, 1)
                },
                'outputs': {
                    'used': total_outputs,
                    'total': output_total,
                    'spare': output_spare,
                    'spare_percent': round(output_spare_percent, 1)
                },
                'power_analysis': {
                    'total_current_ma': total_current,
                    'max_allowed_ma': int(max_allowed),
                    'expansion_power_needed': expansion_power_needed,
                    'current_margin_ma': int(max_allowed - total_current) if not expansion_power_needed else 0
                }
            },
            'modules': modules
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/generate-estimate', methods=['POST'])
def generate_estimate():
    """Generate estimate from wizard configuration"""
    try:
        config = request.json
        
        # Validate required fields
        project_id = config.get('project_id')
        desk_name = config.get('desk_name')
        
        if not project_id or not desk_name:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Generate unique estimate number
        estimate_number = f"OD-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Get current labor rates
        conn = sqlite3.connect('estimates.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT engineering_rate, panel_shop_rate, machine_assembly_rate
            FROM labor_rates WHERE is_current = 1 ORDER BY created_at DESC LIMIT 1
        ''')
        rates = cursor.fetchone()
        conn.close()
        
        eng_rate, panel_rate, machine_rate = rates or (145.00, 125.00, 125.00)
        
        # Create estimate
        estimate = Estimate(
            project_id=project_id,
            estimate_number=estimate_number,
            estimate_name=f"{desk_name} - Operator Desk",
            description=f"Operator desk configuration generated by wizard\\nDesk Type: {config.get('desk_type', 'Not specified')}\\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            engineering_rate=eng_rate,
            panel_shop_rate=panel_rate,
            machine_assembly_rate=machine_rate,
            rate_snapshot_date=date.today()
        )
        
        db.session.add(estimate)
        db.session.flush()
        
        # Generate complete BOM from wizard configuration
        bom_compiler = OperatorDeskBOMCompiler(config, estimate.estimate_id)
        assemblies_created = bom_compiler.compile_and_create_assemblies()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'estimate_id': estimate.estimate_id,
            'estimate_number': estimate.estimate_number,
            'assemblies_created': len(assemblies_created),
            'redirect_url': url_for('estimates.detail_estimate', estimate_id=estimate.estimate_id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

class OperatorDeskBOMCompiler:
    def __init__(self, wizard_config, estimate_id):
        self.config = wizard_config
        self.estimate_id = estimate_id
        
    def compile_and_create_assemblies(self):
        """Compile complete BOM and create assemblies with parts"""
        assemblies_created = []
        
        # 1. Create Operator Controls Assembly
        controls_assembly = self.create_operator_controls_assembly()
        if controls_assembly:
            assemblies_created.append(controls_assembly)
        
        # 2. Create 1734 I/O System Assembly
        io_assembly = self.create_io_system_assembly()
        if io_assembly:
            assemblies_created.append(io_assembly)
        
        # 3. Add Standard Components as Individual Components
        self.add_standard_components_to_estimate()
        
        return assemblies_created
    
    def create_operator_controls_assembly(self):
        """Create assembly for operator control components"""
        controls = self.config.get('controls', {})
        
        # Check if any controls are specified
        total_controls = sum(qty for qty in controls.values() if isinstance(qty, int))
        if total_controls == 0:
            return None
        
        # Create assembly
        assembly = Assembly(
            estimate_id=self.estimate_id,
            assembly_name="Operator Controls",
            description="AB 800T Series operator interface components",
            engineering_hours=2.0 + (total_controls * 0.25),  # Base + per control
            panel_shop_hours=4.0 + (total_controls * 0.5),    # Base + installation time
            machine_assembly_hours=1.0
        )
        
        db.session.add(assembly)
        db.session.flush()
        
        # Add control parts to assembly
        control_part_mapping = {
            'momentary_pb': {'search_terms': ['800T', 'momentary', 'pushbutton'], 'exclude': ['illuminated']},
            'illuminated_pb': {'search_terms': ['800T', 'illuminated', 'pushbutton'], 'exclude': []},
            'pilot_light': {'search_terms': ['800T', 'pilot', 'light'], 'exclude': []},
            'estop': {'search_terms': ['800T', 'emergency', 'stop'], 'exclude': []},
            'selector_2pos': {'search_terms': ['800T', 'selector', '2'], 'exclude': []},
            'selector_3pos': {'search_terms': ['800T', 'selector', '3'], 'exclude': []},
            'trap_key': {'search_terms': ['800T', 'key', 'selector'], 'exclude': []}
        }
        
        for control_type, quantity in controls.items():
            if quantity > 0 and control_type in control_part_mapping:
                part = self.find_part_by_criteria(control_part_mapping[control_type])
                if part:
                    assembly_part = AssemblyPart(
                        assembly_id=assembly.assembly_id,
                        part_id=part.part_id,
                        quantity=quantity,
                        notes=f"Added by operator desk wizard"
                    )
                    db.session.add(assembly_part)
                else:
                    # Create placeholder part if not found
                    placeholder_part = self.create_placeholder_part(control_type, quantity)
                    if placeholder_part:
                        assembly_part = AssemblyPart(
                            assembly_id=assembly.assembly_id,
                            part_id=placeholder_part.part_id,
                            quantity=quantity,
                            notes=f"Placeholder part - Added by operator desk wizard"
                        )
                        db.session.add(assembly_part)
        
        return assembly
    
    def create_io_system_assembly(self):
        """Create assembly for 1734 I/O system"""
        controls = self.config.get('controls', {})
        
        # Calculate I/O requirements
        io_result = self.calculate_io_requirements(controls)
        if not io_result['modules']:
            return None
        
        # Create assembly
        total_modules = len(io_result['modules'])
        assembly = Assembly(
            estimate_id=self.estimate_id,
            assembly_name="1734 Point I/O System",
            description=f"Allen Bradley 1734 I/O system with {total_modules} modules",
            engineering_hours=4.0 + (total_modules * 0.5),  # Base + per module
            panel_shop_hours=6.0 + (total_modules * 0.75),  # Base + wiring time
            machine_assembly_hours=2.0
        )
        
        db.session.add(assembly)
        db.session.flush()
        
        # Add standard 1734 components (always included)
        standard_1734_parts = [
            {'part_number': '1734-AENTR', 'quantity': 1},
            {'part_number': '1734-EP', 'quantity': 1}
        ]
        
        for std_part in standard_1734_parts:
            part = self.find_part_by_exact_number(std_part['part_number'])
            if part:
                assembly_part = AssemblyPart(
                    assembly_id=assembly.assembly_id,
                    part_id=part.part_id,
                    quantity=std_part['quantity'],
                    notes="Standard 1734 system component"
                )
                db.session.add(assembly_part)
            else:
                # Create placeholder
                placeholder = self.create_placeholder_part_by_number(std_part['part_number'], std_part['quantity'])
                if placeholder:
                    assembly_part = AssemblyPart(
                        assembly_id=assembly.assembly_id,
                        part_id=placeholder.part_id,
                        quantity=std_part['quantity'],
                        notes="Placeholder - Standard 1734 system component"
                    )
                    db.session.add(assembly_part)
        
        # Add calculated I/O modules
        for module in io_result['modules']:
            # Add the module itself
            part = self.find_part_by_exact_number(module['part_number'])
            if part:
                assembly_part = AssemblyPart(
                    assembly_id=assembly.assembly_id,
                    part_id=part.part_id,
                    quantity=1,
                    notes=f"I/O Module - {module['points_used']}/{module['points_available']} points used"
                )
                db.session.add(assembly_part)
            else:
                # Create placeholder
                placeholder = self.create_placeholder_part_by_number(module['part_number'], 1)
                if placeholder:
                    assembly_part = AssemblyPart(
                        assembly_id=assembly.assembly_id,
                        part_id=placeholder.part_id,
                        quantity=1,
                        notes=f"Placeholder - I/O Module - {module['points_used']}/{module['points_available']} points used"
                    )
                    db.session.add(assembly_part)
            
            # Add terminal bases for this module
            if module['wiring_bases_needed'] > 0:
                tb_part = self.find_part_by_exact_number('1734-TB')
                if tb_part:
                    assembly_part = AssemblyPart(
                        assembly_id=assembly.assembly_id,
                        part_id=tb_part.part_id,
                        quantity=module['wiring_bases_needed'],
                        notes=f"Terminal base for {module['part_number']}"
                    )
                    db.session.add(assembly_part)
                else:
                    # Create placeholder
                    placeholder = self.create_placeholder_part_by_number('1734-TB', module['wiring_bases_needed'])
                    if placeholder:
                        assembly_part = AssemblyPart(
                            assembly_id=assembly.assembly_id,
                            part_id=placeholder.part_id,
                            quantity=module['wiring_bases_needed'],
                            notes=f"Placeholder - Terminal base for {module['part_number']}"
                        )
                        db.session.add(assembly_part)
        
        return assembly
    
    def add_standard_components_to_estimate(self):
        """Add standard components as individual estimate components"""
        standard_components = self.config.get('standard_components', {})
        
        # Default standard components if not specified
        default_components = [
            {'name': '24VDC Power Supply (5A)', 'search_terms': ['24VDC', 'power supply'], 'fallback_price': 142.50},
            {'name': 'Fuse Holders', 'search_terms': ['fuse holder'], 'fallback_price': 12.30, 'quantity': 4},
            {'name': 'Temperature Switch (100°F)', 'search_terms': ['temperature switch'], 'fallback_price': 89.25},
            {'name': 'Cooling Fan (120CFM)', 'search_terms': ['cooling fan'], 'fallback_price': 67.80},
            {'name': '120VAC Receptacle (GFCI)', 'search_terms': ['receptacle', 'GFCI'], 'fallback_price': 28.50},
            {'name': 'Internal LED Lighting', 'search_terms': ['LED light'], 'fallback_price': 34.20}
        ]
        
        for component in default_components:
            # Check if component is enabled (default to enabled)
            component_key = component['name'].lower().replace(' ', '_').replace('(', '').replace(')', '')
            if standard_components.get(component_key, True):  # Default enabled if not specified
                
                quantity = component.get('quantity', 1)
                part = self.find_part_by_criteria({'search_terms': component['search_terms']})
                
                if part:
                    estimate_component = EstimateComponent(
                        estimate_id=self.estimate_id,
                        part_id=part.part_id,
                        component_name=component['name'],
                        description=part.description,
                        part_number=part.part_number,
                        manufacturer=part.manufacturer,
                        unit_price=part.current_price,
                        quantity=quantity,
                        category='Standard Components',
                        notes='Added by operator desk wizard'
                    )
                else:
                    # Create as custom component
                    estimate_component = EstimateComponent(
                        estimate_id=self.estimate_id,
                        component_name=component['name'],
                        description=f"Standard operator desk component",
                        unit_price=component['fallback_price'],
                        quantity=quantity,
                        category='Standard Components',
                        notes='Placeholder component - Added by operator desk wizard'
                    )
                
                db.session.add(estimate_component)
    
    def find_part_by_criteria(self, criteria):
        """Find part by search criteria"""
        search_terms = criteria.get('search_terms', [])
        exclude_terms = criteria.get('exclude', [])
        
        if not search_terms:
            return None
        
        # Build query
        query = Parts.query
        
        # Add search terms (must contain all terms)
        for term in search_terms:
            query = query.filter(
                db.or_(
                    Parts.description.ilike(f'%{term}%'),
                    Parts.part_number.ilike(f'%{term}%'),
                    Parts.manufacturer.ilike(f'%{term}%')
                )
            )
        
        # Exclude terms
        for exclude in exclude_terms:
            query = query.filter(~Parts.description.ilike(f'%{exclude}%'))
        
        return query.first()
    
    def find_part_by_exact_number(self, part_number):
        """Find part by exact part number"""
        return Parts.query.filter(Parts.part_number == part_number).first()
    
    def create_placeholder_part(self, control_type, quantity):
        """Create placeholder part for missing components"""
        control_names = {
            'momentary_pb': 'AB 800T Momentary Pushbutton',
            'illuminated_pb': 'AB 800T Illuminated Pushbutton',
            'pilot_light': 'AB 800T Pilot Light',
            'estop': 'AB 800T Emergency Stop',
            'selector_2pos': 'AB 800T 2-Position Selector',
            'selector_3pos': 'AB 800T 3-Position Selector',
            'trap_key': 'AB 800T Key Selector Switch'
        }
        
        placeholder_prices = {
            'momentary_pb': 45.00,
            'illuminated_pb': 75.00,
            'pilot_light': 35.00,
            'estop': 125.00,
            'selector_2pos': 85.00,
            'selector_3pos': 95.00,
            'trap_key': 150.00
        }
        
        part_name = control_names.get(control_type, f'Unknown Control Type: {control_type}')
        price = placeholder_prices.get(control_type, 50.00)
        
        # Create placeholder part
        part = Parts(
            manufacturer='Allen Bradley',
            part_number=f'800T-{control_type.upper()}-PLACEHOLDER',
            description=part_name + ' (PLACEHOLDER)',
            category='Operator Interface'
        )
        
        db.session.add(part)
        db.session.flush()
        
        # Add price history
        part.update_price(price, "Placeholder part created by wizard", "wizard")
        
        return part
    
    def create_placeholder_part_by_number(self, part_number, quantity):
        """Create placeholder part by part number"""
        placeholder_prices = {
            '1734-AENTR': 850.00,
            '1734-EP': 25.00,
            '1734-IB8': 275.00,
            '1734-IB8S': 425.00,
            '1734-OB8': 285.00,
            '1734-TB': 45.00,
            '1734-EP24DC': 325.00
        }
        
        price = placeholder_prices.get(part_number, 100.00)
        
        part = Parts(
            manufacturer='Allen Bradley',
            part_number=part_number,
            description=f'{part_number} (PLACEHOLDER)',
            category='1734 Point I/O'
        )
        
        db.session.add(part)
        db.session.flush()
        
        # Add price history
        part.update_price(price, "Placeholder part created by wizard", "wizard")
        
        return part
    
    def calculate_io_requirements(self, controls):
        """Calculate I/O requirements (reuse logic from API endpoint)"""
        total_standard_inputs = 0
        total_safety_inputs = 0
        total_outputs = 0
        
        for control_type, qty in controls.items():
            if control_type in DIGITAL_IO_MAP:
                io_map = DIGITAL_IO_MAP[control_type]
                total_standard_inputs += io_map['standard_inputs'] * qty
                total_safety_inputs += io_map['safety_inputs'] * qty
                total_outputs += io_map['outputs'] * qty
        
        # Add 20% spare capacity (rounded up)
        required_standard_inputs = math.ceil(total_standard_inputs * 1.2)
        required_safety_inputs = math.ceil(total_safety_inputs * 1.2)
        required_outputs = math.ceil(total_outputs * 1.2)
        
        # Calculate modules needed
        modules = []
        
        # Standard input modules
        if required_standard_inputs > 0:
            input_modules = math.ceil(required_standard_inputs / 8)
            for i in range(input_modules):
                modules.append({
                    'part_number': '1734-IB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_standard_inputs - (i * 8)),
                    'points_available': 8
                })
        
        # Safety input modules
        if required_safety_inputs > 0:
            safety_modules = math.ceil(required_safety_inputs / 8)
            for i in range(safety_modules):
                modules.append({
                    'part_number': '1734-IB8S',
                    'wiring_bases_needed': 2,
                    'points_used': min(8, required_safety_inputs - (i * 8)),
                    'points_available': 8
                })
        
        # Output modules
        if required_outputs > 0:
            output_modules = math.ceil(required_outputs / 8)
            for i in range(output_modules):
                modules.append({
                    'part_number': '1734-OB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_outputs - (i * 8)),
                    'points_available': 8
                })
        
        # Check if expansion power needed
        total_current = IO_MODULE_POWER['1734-AENTR']['backplane_current_ma'] + IO_MODULE_POWER['1734-EP']['backplane_current_ma']
        for module in modules:
            total_current += IO_MODULE_POWER[module['part_number']]['backplane_current_ma']
        
        max_allowed = BACKPLANE_LIMITS['standard_backplane_max_ma'] * (1 - BACKPLANE_LIMITS['safety_margin_percent'] / 100)
        if total_current > max_allowed:
            modules.append({
                'part_number': '1734-EP24DC',
                'wiring_bases_needed': 0,
                'points_used': 0,
                'points_available': 0
            })
        
        return {'modules': modules}

@bp.route('/api/preview-bom', methods=['POST'])
def preview_bom():
    """Preview BOM before generating estimate"""
    try:
        config = request.json
        
        # Create a temporary BOM compiler to preview parts
        preview_compiler = BOMPreviewCompiler(config)
        bom_preview = preview_compiler.generate_preview()
        
        return jsonify({
            'success': True,
            'bom_preview': bom_preview
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

class BOMPreviewCompiler:
    def __init__(self, wizard_config):
        self.config = wizard_config
    
    def generate_preview(self):
        """Generate BOM preview without creating database records"""
        assemblies = []
        individual_components = []
        
        # 1. Preview Operator Controls Assembly
        controls_assembly = self.preview_operator_controls_assembly()
        if controls_assembly:
            assemblies.append(controls_assembly)
        
        # 2. Preview 1734 I/O System Assembly
        io_assembly = self.preview_io_system_assembly()
        if io_assembly:
            assemblies.append(io_assembly)
        
        # 3. Preview Standard Components
        standard_components = self.preview_standard_components()
        individual_components.extend(standard_components)
        
        # 4. Calculate totals
        material_total = 0
        labor_total = 0
        
        for assembly in assemblies:
            material_total += assembly['material_total']
            labor_total += assembly['labor_total']
        
        for component in individual_components:
            material_total += component['total_price']
        
        return {
            'assemblies': assemblies,
            'individual_components': individual_components,
            'totals': {
                'material_total': material_total,
                'labor_total': labor_total,
                'grand_total': material_total + labor_total
            }
        }
    
    def preview_operator_controls_assembly(self):
        """Preview operator controls assembly"""
        controls = self.config.get('controls', {})
        
        # Check if any controls are specified
        total_controls = sum(qty for qty in controls.values() if isinstance(qty, int))
        if total_controls == 0:
            return None
        
        # Calculate labor hours
        engineering_hours = 2.0 + (total_controls * 0.25)
        panel_shop_hours = 4.0 + (total_controls * 0.5)
        machine_assembly_hours = 1.0
        
        # Calculate labor costs (using default rates)
        labor_total = (engineering_hours * 145.0) + (panel_shop_hours * 125.0) + (machine_assembly_hours * 125.0)
        
        # Preview control parts
        parts = []
        material_total = 0
        
        control_part_mapping = {
            'momentary_pb': {'name': 'AB 800T Momentary Pushbutton', 'price': 45.00},
            'illuminated_pb': {'name': 'AB 800T Illuminated Pushbutton', 'price': 75.00},
            'pilot_light': {'name': 'AB 800T Pilot Light', 'price': 35.00},
            'estop': {'name': 'AB 800T Emergency Stop', 'price': 125.00},
            'selector_2pos': {'name': 'AB 800T 2-Position Selector', 'price': 85.00},
            'selector_3pos': {'name': 'AB 800T 3-Position Selector', 'price': 95.00},
            'trap_key': {'name': 'AB 800T Key Selector Switch', 'price': 150.00}
        }
        
        for control_type, quantity in controls.items():
            if quantity > 0 and control_type in control_part_mapping:
                part_info = control_part_mapping[control_type]
                # Try to find actual part first
                actual_part = self.find_part_by_criteria({
                    'search_terms': ['800T', control_type.replace('_', ' ')],
                    'exclude': []
                })
                
                if actual_part:
                    part_data = {
                        'name': actual_part.description,
                        'part_number': actual_part.part_number,
                        'manufacturer': actual_part.manufacturer,
                        'unit_price': float(actual_part.current_price),
                        'quantity': quantity,
                        'total_price': float(actual_part.current_price) * quantity,
                        'notes': 'From parts database'
                    }
                else:
                    part_data = {
                        'name': part_info['name'],
                        'part_number': f'800T-{control_type.upper()}-PLACEHOLDER',
                        'manufacturer': 'Allen Bradley',
                        'unit_price': part_info['price'],
                        'quantity': quantity,
                        'total_price': part_info['price'] * quantity,
                        'notes': 'Placeholder pricing'
                    }
                
                parts.append(part_data)
                material_total += part_data['total_price']
        
        return {
            'assembly_name': 'Operator Controls',
            'description': f'AB 800T Series operator interface components ({total_controls} components)',
            'parts': parts,
            'material_total': material_total,
            'labor_hours': {
                'engineering': engineering_hours,
                'panel_shop': panel_shop_hours,
                'machine_assembly': machine_assembly_hours
            },
            'labor_total': labor_total
        }
    
    def preview_io_system_assembly(self):
        """Preview 1734 I/O system assembly"""
        controls = self.config.get('controls', {})
        
        # Calculate I/O requirements
        io_result = self.calculate_io_requirements(controls)
        if not io_result['modules']:
            return None
        
        total_modules = len(io_result['modules'])
        
        # Calculate labor hours
        engineering_hours = 4.0 + (total_modules * 0.5)
        panel_shop_hours = 6.0 + (total_modules * 0.75)
        machine_assembly_hours = 2.0
        
        labor_total = (engineering_hours * 145.0) + (panel_shop_hours * 125.0) + (machine_assembly_hours * 125.0)
        
        # Preview I/O parts
        parts = []
        material_total = 0
        
        # Standard 1734 components
        standard_parts = [
            {'part_number': '1734-AENTR', 'name': '1734-AENTR Ethernet Adapter', 'price': 850.00, 'quantity': 1},
            {'part_number': '1734-EP', 'name': '1734-EP End Cap', 'price': 25.00, 'quantity': 1}
        ]
        
        for std_part in standard_parts:
            # Try to find actual part
            actual_part = self.find_part_by_exact_number(std_part['part_number'])
            if actual_part:
                part_data = {
                    'name': actual_part.description,
                    'part_number': actual_part.part_number,
                    'manufacturer': actual_part.manufacturer,
                    'unit_price': float(actual_part.current_price),
                    'quantity': std_part['quantity'],
                    'total_price': float(actual_part.current_price) * std_part['quantity'],
                    'notes': 'From parts database'
                }
            else:
                part_data = {
                    'name': std_part['name'],
                    'part_number': std_part['part_number'],
                    'manufacturer': 'Allen Bradley',
                    'unit_price': std_part['price'],
                    'quantity': std_part['quantity'],
                    'total_price': std_part['price'] * std_part['quantity'],
                    'notes': 'Placeholder pricing'
                }
            
            parts.append(part_data)
            material_total += part_data['total_price']
        
        # I/O Modules and terminal bases
        module_prices = {
            '1734-IB8': 275.00,
            '1734-IB8S': 425.00,
            '1734-OB8': 285.00,
            '1734-TB': 45.00,
            '1734-EP24DC': 325.00
        }
        
        for module in io_result['modules']:
            # Add the module
            actual_part = self.find_part_by_exact_number(module['part_number'])
            if actual_part:
                part_data = {
                    'name': actual_part.description,
                    'part_number': actual_part.part_number,
                    'manufacturer': actual_part.manufacturer,
                    'unit_price': float(actual_part.current_price),
                    'quantity': 1,
                    'total_price': float(actual_part.current_price),
                    'notes': f"I/O Module - {module.get('points_used', 0)}/{module.get('points_available', 8)} points used"
                }
            else:
                price = module_prices.get(module['part_number'], 100.00)
                part_data = {
                    'name': f"{module['part_number']} I/O Module",
                    'part_number': module['part_number'],
                    'manufacturer': 'Allen Bradley',
                    'unit_price': price,
                    'quantity': 1,
                    'total_price': price,
                    'notes': f"Placeholder - I/O Module - {module.get('points_used', 0)}/{module.get('points_available', 8)} points used"
                }
            
            parts.append(part_data)
            material_total += part_data['total_price']
            
            # Add terminal bases
            if module.get('wiring_bases_needed', 0) > 0:
                tb_part = self.find_part_by_exact_number('1734-TB')
                if tb_part:
                    tb_data = {
                        'name': tb_part.description,
                        'part_number': tb_part.part_number,
                        'manufacturer': tb_part.manufacturer,
                        'unit_price': float(tb_part.current_price),
                        'quantity': module['wiring_bases_needed'],
                        'total_price': float(tb_part.current_price) * module['wiring_bases_needed'],
                        'notes': f"Terminal base for {module['part_number']}"
                    }
                else:
                    tb_data = {
                        'name': '1734-TB Terminal Base',
                        'part_number': '1734-TB',
                        'manufacturer': 'Allen Bradley',
                        'unit_price': 45.00,
                        'quantity': module['wiring_bases_needed'],
                        'total_price': 45.00 * module['wiring_bases_needed'],
                        'notes': f"Placeholder - Terminal base for {module['part_number']}"
                    }
                
                parts.append(tb_data)
                material_total += tb_data['total_price']
        
        return {
            'assembly_name': '1734 Point I/O System',
            'description': f'Allen Bradley 1734 I/O system with {total_modules} modules',
            'parts': parts,
            'material_total': material_total,
            'labor_hours': {
                'engineering': engineering_hours,
                'panel_shop': panel_shop_hours,
                'machine_assembly': machine_assembly_hours
            },
            'labor_total': labor_total
        }
    
    def preview_standard_components(self):
        """Preview standard components"""
        standard_components = self.config.get('standard_components', {})
        components = []
        
        default_components = [
            {'name': '24VDC Power Supply (5A)', 'search_terms': ['24VDC', 'power supply'], 'fallback_price': 142.50, 'key': 'power_supply'},
            {'name': 'Fuse Holders', 'search_terms': ['fuse holder'], 'fallback_price': 12.30, 'quantity': 4, 'key': 'fuse_holders'},
            {'name': 'Temperature Switch (100°F)', 'search_terms': ['temperature switch'], 'fallback_price': 89.25, 'key': 'temp_switch'},
            {'name': 'Cooling Fan (120CFM)', 'search_terms': ['cooling fan'], 'fallback_price': 67.80, 'key': 'cooling_fan'},
            {'name': '120VAC Receptacle (GFCI)', 'search_terms': ['receptacle', 'GFCI'], 'fallback_price': 28.50, 'key': 'receptacle'},
            {'name': 'Internal LED Lighting', 'search_terms': ['LED light'], 'fallback_price': 34.20, 'key': 'lighting'}
        ]
        
        for component in default_components:
            # Check if component is enabled (default to enabled)
            if standard_components.get(component['key'], True):
                quantity = component.get('quantity', 1)
                
                # Try to find actual part
                actual_part = self.find_part_by_criteria({'search_terms': component['search_terms']})
                
                if actual_part:
                    comp_data = {
                        'name': actual_part.description,
                        'part_number': actual_part.part_number,
                        'manufacturer': actual_part.manufacturer,
                        'unit_price': float(actual_part.current_price),
                        'quantity': quantity,
                        'total_price': float(actual_part.current_price) * quantity,
                        'category': 'Standard Components',
                        'notes': 'From parts database'
                    }
                else:
                    comp_data = {
                        'name': component['name'],
                        'part_number': 'TBD',
                        'manufacturer': 'TBD',
                        'unit_price': component['fallback_price'],
                        'quantity': quantity,
                        'total_price': component['fallback_price'] * quantity,
                        'category': 'Standard Components',
                        'notes': 'Placeholder pricing'
                    }
                
                components.append(comp_data)
        
        return components
    
    def find_part_by_criteria(self, criteria):
        """Find part by search criteria (same as main compiler)"""
        search_terms = criteria.get('search_terms', [])
        exclude_terms = criteria.get('exclude', [])
        
        if not search_terms:
            return None
        
        # Build query
        query = Parts.query
        
        # Add search terms (must contain all terms)
        for term in search_terms:
            query = query.filter(
                db.or_(
                    Parts.description.ilike(f'%{term}%'),
                    Parts.part_number.ilike(f'%{term}%'),
                    Parts.manufacturer.ilike(f'%{term}%')
                )
            )
        
        # Exclude terms
        for exclude in exclude_terms:
            query = query.filter(~Parts.description.ilike(f'%{exclude}%'))
        
        return query.first()
    
    def find_part_by_exact_number(self, part_number):
        """Find part by exact part number"""
        return Parts.query.filter(Parts.part_number == part_number).first()
    
    def calculate_io_requirements(self, controls):
        """Calculate I/O requirements (same as main compiler)"""
        total_standard_inputs = 0
        total_safety_inputs = 0
        total_outputs = 0
        
        for control_type, qty in controls.items():
            if control_type in DIGITAL_IO_MAP:
                io_map = DIGITAL_IO_MAP[control_type]
                total_standard_inputs += io_map['standard_inputs'] * qty
                total_safety_inputs += io_map['safety_inputs'] * qty
                total_outputs += io_map['outputs'] * qty
        
        # Add 20% spare capacity (rounded up)
        required_standard_inputs = math.ceil(total_standard_inputs * 1.2)
        required_safety_inputs = math.ceil(total_safety_inputs * 1.2)
        required_outputs = math.ceil(total_outputs * 1.2)
        
        # Calculate modules needed
        modules = []
        
        # Standard input modules
        if required_standard_inputs > 0:
            input_modules = math.ceil(required_standard_inputs / 8)
            for i in range(input_modules):
                modules.append({
                    'part_number': '1734-IB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_standard_inputs - (i * 8)),
                    'points_available': 8
                })
        
        # Safety input modules
        if required_safety_inputs > 0:
            safety_modules = math.ceil(required_safety_inputs / 8)
            for i in range(safety_modules):
                modules.append({
                    'part_number': '1734-IB8S',
                    'wiring_bases_needed': 2,
                    'points_used': min(8, required_safety_inputs - (i * 8)),
                    'points_available': 8
                })
        
        # Output modules
        if required_outputs > 0:
            output_modules = math.ceil(required_outputs / 8)
            for i in range(output_modules):
                modules.append({
                    'part_number': '1734-OB8',
                    'wiring_bases_needed': 1,
                    'points_used': min(8, required_outputs - (i * 8)),
                    'points_available': 8
                })
        
        # Check if expansion power needed
        total_current = IO_MODULE_POWER['1734-AENTR']['backplane_current_ma'] + IO_MODULE_POWER['1734-EP']['backplane_current_ma']
        for module in modules:
            total_current += IO_MODULE_POWER[module['part_number']]['backplane_current_ma']
        
        max_allowed = BACKPLANE_LIMITS['standard_backplane_max_ma'] * (1 - BACKPLANE_LIMITS['safety_margin_percent'] / 100)
        if total_current > max_allowed:
            modules.append({
                'part_number': '1734-EP24DC',
                'wiring_bases_needed': 0,
                'points_used': 0,
                'points_available': 0
            })
        
        return {'modules': modules}
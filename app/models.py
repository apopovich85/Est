from app import db
from datetime import datetime
from sqlalchemy import event

class PartCategory(db.Model):
    __tablename__ = 'part_categories'
    
    category_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to parts
    parts = db.relationship('Parts', backref='part_category', lazy='dynamic')
    
    def __repr__(self):
        return f'<PartCategory {self.name}>'
    
    @staticmethod
    def get_or_create(name):
        """Get existing category or create new one"""
        if not name or not name.strip():
            return None
            
        name = name.strip()
        category = PartCategory.query.filter_by(name=name).first()
        
        if not category:
            category = PartCategory(name=name)
            db.session.add(category)
            db.session.flush()  # Get the ID without committing
            
        return category

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='Viewer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    __tablename__ = 'projects'
    
    project_id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimates = db.relationship('Estimate', backref='project', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.project_name}>'
    
    def total_value(self):
        return sum(estimate.calculated_total for estimate in self.estimates)
    
    def total_project_hours(self):
        """Calculate total hours across all estimates in project"""
        return sum(estimate.total_hours for estimate in self.estimates)
    
    def total_project_engineering_hours(self):
        """Calculate total engineering hours across all estimates in project"""
        return sum(estimate.total_engineering_hours for estimate in self.estimates)
    
    def total_project_panel_shop_hours(self):
        """Calculate total panel shop hours across all estimates in project"""
        return sum(estimate.total_panel_shop_hours for estimate in self.estimates)
    
    def total_project_machine_assembly_hours(self):
        """Calculate total machine assembly hours across all estimates in project"""
        return sum(estimate.total_machine_assembly_hours for estimate in self.estimates)
    
    def total_project_labor_cost(self):
        """Calculate total labor cost across all estimates in project"""
        return sum(estimate.total_labor_cost for estimate in self.estimates)
    
    def total_project_grand_total(self):
        """Calculate total project value including materials and labor"""
        return sum(estimate.grand_total for estimate in self.estimates)

class Estimate(db.Model):
    __tablename__ = 'estimates'
    
    estimate_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
    estimate_number = db.Column(db.String(100), unique=True, nullable=False)
    estimate_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    total_value = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Labor rate snapshot (preserves rates used when estimate was created)
    engineering_rate = db.Column(db.Numeric(8, 2), default=145.00)
    panel_shop_rate = db.Column(db.Numeric(8, 2), default=125.00)
    machine_assembly_rate = db.Column(db.Numeric(8, 2), default=125.00)
    rate_snapshot_date = db.Column(db.Date)
    
    # Relationships
    assemblies = db.relationship('Assembly', backref='estimate', cascade='all, delete-orphan')
    individual_components = db.relationship('EstimateComponent', backref='estimate', cascade='all, delete-orphan')
    
    @property
    def calculated_total(self):
        """Calculate the total value of all assemblies and individual components in this estimate"""
        assembly_total = sum(assembly.calculated_total for assembly in self.assemblies)
        component_total = sum(comp.total_price for comp in self.individual_components)
        return assembly_total + component_total
    
    @property
    def total_engineering_hours(self):
        """Calculate total engineering hours across all assemblies"""
        return sum(float(assembly.engineering_hours or 0) for assembly in self.assemblies)
    
    @property
    def total_panel_shop_hours(self):
        """Calculate total panel shop hours across all assemblies"""
        return sum(float(assembly.panel_shop_hours or 0) for assembly in self.assemblies)
    
    @property
    def total_machine_assembly_hours(self):
        """Calculate total machine assembly hours across all assemblies"""
        return sum(float(assembly.machine_assembly_hours or 0) for assembly in self.assemblies)
    
    @property
    def total_hours(self):
        """Calculate total hours across all labor types and assemblies"""
        return self.total_engineering_hours + self.total_panel_shop_hours + self.total_machine_assembly_hours
    
    @property
    def total_engineering_cost(self):
        """Calculate total engineering cost across all assemblies"""
        return sum(assembly.calculated_engineering_cost for assembly in self.assemblies)
    
    @property
    def total_panel_shop_cost(self):
        """Calculate total panel shop cost across all assemblies"""
        return sum(assembly.calculated_panel_shop_cost for assembly in self.assemblies)
    
    @property
    def total_machine_assembly_cost(self):
        """Calculate total machine assembly cost across all assemblies"""
        return sum(assembly.calculated_machine_assembly_cost for assembly in self.assemblies)
    
    @property
    def total_labor_cost(self):
        """Calculate total labor cost across all assemblies"""
        return self.total_engineering_cost + self.total_panel_shop_cost + self.total_machine_assembly_cost
    
    @property
    def grand_total(self):
        """Calculate grand total including materials and labor"""
        return self.calculated_total + self.total_labor_cost
    
    def __repr__(self):
        return f'<Estimate {self.estimate_number}>'

class Assembly(db.Model):
    __tablename__ = 'assemblies'
    
    assembly_id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey('estimates.estimate_id'), nullable=False)
    assembly_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    assembly_total = db.Column(db.Numeric(12, 2), default=0.00)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Link to standard assembly if created from one
    standard_assembly_id = db.Column(db.Integer, db.ForeignKey('standard_assemblies.standard_assembly_id'), nullable=True)
    standard_assembly_version = db.Column(db.String(20), nullable=True)  # Version used when created
    quantity = db.Column(db.Numeric(10, 3), default=1.0)  # How many of this assembly (for standard assembly multiplier)
    
    # Time estimation fields
    engineering_hours = db.Column(db.Numeric(8, 2), default=0.0)
    panel_shop_hours = db.Column(db.Numeric(8, 2), default=0.0)
    machine_assembly_hours = db.Column(db.Numeric(8, 2), default=0.0)
    estimated_by = db.Column(db.String(100))
    time_estimate_notes = db.Column(db.Text)
    
    # Labor cost fields (calculated from hours * rates)
    engineering_cost = db.Column(db.Numeric(10, 2), default=0.0)
    panel_shop_cost = db.Column(db.Numeric(10, 2), default=0.0)
    machine_assembly_cost = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Relationships - now uses AssemblyPart instead of Component
    assembly_parts = db.relationship('AssemblyPart', backref='assembly', cascade='all, delete-orphan')
    
    @property
    def calculated_total(self):
        """Calculate the total value of all parts in this assembly"""
        return sum(ap.total_price for ap in self.assembly_parts)
    
    @property
    def total_hours(self):
        """Calculate total hours across all labor types"""
        return float(self.engineering_hours or 0) + float(self.panel_shop_hours or 0) + float(self.machine_assembly_hours or 0)
    
    @property
    def calculated_engineering_cost(self):
        """Calculate engineering cost based on hours * estimate's engineering rate"""
        rate = float(self.estimate.engineering_rate) if self.estimate else 145.0
        return float(self.engineering_hours or 0) * rate
    
    @property
    def calculated_panel_shop_cost(self):
        """Calculate panel shop cost based on hours * estimate's panel shop rate"""
        rate = float(self.estimate.panel_shop_rate) if self.estimate else 125.0
        return float(self.panel_shop_hours or 0) * rate
    
    @property
    def calculated_machine_assembly_cost(self):
        """Calculate machine assembly cost based on hours * estimate's machine assembly rate"""
        rate = float(self.estimate.machine_assembly_rate) if self.estimate else 125.0
        return float(self.machine_assembly_hours or 0) * rate
    
    @property
    def total_labor_cost(self):
        """Calculate total labor cost across all disciplines"""
        return self.calculated_engineering_cost + self.calculated_panel_shop_cost + self.calculated_machine_assembly_cost
    
    @property
    def total_assembly_cost(self):
        """Calculate total assembly cost (materials + labor)"""
        return self.calculated_total + self.total_labor_cost
    
    def __repr__(self):
        return f'<Assembly {self.assembly_name}>'

class AssemblyPart(db.Model):
    """Junction table linking assemblies to parts with quantity and assembly-specific data"""
    __tablename__ = 'assembly_parts'
    
    assembly_part_id = db.Column(db.Integer, primary_key=True)
    assembly_id = db.Column(db.Integer, db.ForeignKey('assemblies.assembly_id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False, default=1.000)
    unit_of_measure = db.Column(db.String(20), default='EA')
    sort_order = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)  # Assembly-specific notes for this part
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = db.relationship('Parts', backref='assembly_parts')
    
    @property
    def unit_price(self):
        """Get current price from the part"""
        return self.part.current_price if self.part else 0.0
    
    @property
    def total_price(self):
        """Calculate total price for this quantity"""
        return self.unit_price * float(self.quantity)
    
    @property
    def component_name(self):
        """Backward compatibility - returns part description"""
        return self.part.description or self.part.part_number
    
    @property 
    def part_number(self):
        """Get part number from the linked part"""
        return self.part.part_number
        
    @property
    def description(self):
        """Get description from the linked part, or use assembly-specific notes"""
        return self.notes or self.part.description
    
    def __repr__(self):
        return f'<AssemblyPart {self.part.part_number} x{self.quantity}>'

class Component(db.Model):
    __tablename__ = 'components'
    
    component_id = db.Column(db.Integer, primary_key=True)
    assembly_id = db.Column(db.Integer, db.ForeignKey('assemblies.assembly_id'), nullable=False)
    component_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    part_number = db.Column(db.String(100))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False, default=1.000)
    unit_of_measure = db.Column(db.String(20), default='EA')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_history = db.relationship('PriceHistory', backref='component', cascade='all, delete-orphan')
    
    @property
    def total_price(self):
        return float(self.unit_price * self.quantity)
    
    def __repr__(self):
        return f'<Component {self.component_name}>'

class EstimateComponent(db.Model):
    """Individual components added directly to estimates (not part of an assembly)"""
    __tablename__ = 'estimate_components'
    
    estimate_component_id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey('estimates.estimate_id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=True)  # Optional - can be custom component
    component_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    part_number = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False, default=1.000)
    unit_of_measure = db.Column(db.String(20), default='EA')
    category = db.Column(db.String(100))
    notes = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = db.relationship('Parts', backref='estimate_components')
    
    @property
    def total_price(self):
        """Calculate total price for this component"""
        return float(self.unit_price * self.quantity)
    
    def __repr__(self):
        return f'<EstimateComponent {self.component_name}>'

class Parts(db.Model):
    __tablename__ = 'parts'
    
    part_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('part_categories.category_id'), nullable=True, index=True)
    model = db.Column(db.String(100))
    rating = db.Column(db.String(50))
    master_item_number = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100), nullable=False, index=True)
    part_number = db.Column(db.String(100), nullable=False, index=True)
    upc = db.Column(db.String(50))
    description = db.Column(db.Text)
    # price column removed - now using PartsPriceHistory table
    # effective_date column removed - now using PartsPriceHistory table
    vendor = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to price history
    price_history = db.relationship('PartsPriceHistory', backref='part', cascade='all, delete-orphan')
    
    @property
    def category(self):
        """Get the category name for backward compatibility"""
        return self.part_category.name if self.part_category else None
    
    @category.setter
    def category(self, value):
        """Set the category by name, creating if necessary"""
        if value:
            category_obj = PartCategory.get_or_create(value)
            self.category_id = category_obj.category_id if category_obj else None
        else:
            self.category_id = None
    
    @property
    def current_price(self):
        """Get the current price from price history"""
        current_history = db.session.query(PartsPriceHistory)\
            .filter_by(part_id=self.part_id, is_current=True)\
            .first()
        
        if current_history:
            return float(current_history.new_price) if current_history.new_price else 0.0
        
        # No current price found
        return 0.0
    
    @property
    def effective_date(self):
        """Get the effective date from the current price history record"""
        current_history = db.session.query(PartsPriceHistory)\
            .filter_by(part_id=self.part_id, is_current=True)\
            .first()
        
        if current_history:
            return current_history.effective_date
        
        # If no current price history, get the most recent effective date
        latest_history = db.session.query(PartsPriceHistory)\
            .filter_by(part_id=self.part_id)\
            .order_by(PartsPriceHistory.changed_at.desc())\
            .first()
        
        return latest_history.effective_date if latest_history else None
    
    def update_price(self, new_price, reason="Price update", source="manual", effective_date=None):
        """Update part price with automatic history tracking"""
        from decimal import Decimal
        
        # Get current price
        old_price = self.current_price
        new_price_decimal = Decimal(str(new_price))
        
        # Only update if price actually changed
        if abs(old_price - float(new_price)) < 0.01:
            return False, "Price unchanged"
        
        # Mark all current prices as not current
        db.session.query(PartsPriceHistory)\
            .filter_by(part_id=self.part_id, is_current=True)\
            .update({'is_current': False})
        
        # Create new price history record
        price_history = PartsPriceHistory(
            part_id=self.part_id,
            old_price=Decimal(str(old_price)) if old_price > 0 else None,
            new_price=new_price_decimal,
            changed_at=datetime.utcnow(),
            changed_reason=reason,
            effective_date=effective_date or datetime.utcnow().date(),
            is_current=True,
            source=source
        )
        
        db.session.add(price_history)
        
        # Update timestamp
        self.updated_at = datetime.utcnow()
        
        return True, f"Price updated from ${old_price:.2f} to ${new_price:.2f}"
    
    def get_price_history(self, limit=None):
        """Get price history for this part"""
        query = db.session.query(PartsPriceHistory)\
            .filter_by(part_id=self.part_id)\
            .order_by(PartsPriceHistory.changed_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def find_by_identifier(identifier):
        """Find part by part_number, master_item_number, or upc"""
        return db.session.query(Parts).filter(
            db.or_(
                Parts.part_number == identifier,
                Parts.master_item_number == identifier,
                Parts.upc == identifier
            )
        ).first()
    
    def __repr__(self):
        return f'<Parts {self.part_number}: {self.description[:50]}>'

class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    history_id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.component_id'), nullable=False)
    old_price = db.Column(db.Numeric(10, 2))
    new_price = db.Column(db.Numeric(10, 2))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changed_reason = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<PriceHistory {self.component_id}: {self.old_price} -> {self.new_price}>'

class PartsPriceHistory(db.Model):
    __tablename__ = 'parts_price_history'
    
    history_id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=False)
    old_price = db.Column(db.Numeric(12, 2))
    new_price = db.Column(db.Numeric(12, 2))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changed_reason = db.Column(db.String(255))
    effective_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False, index=True)
    source = db.Column(db.String(50), default='manual')  # manual, csv_import, api, etc.
    
    def __repr__(self):
        return f'<PartsPriceHistory {self.part_id}: {self.old_price} -> {self.new_price} ({self.source})>'

class StandardAssembly(db.Model):
    """Master standard assembly definitions with versioning"""
    __tablename__ = 'standard_assemblies'
    
    standard_assembly_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    assembly_number = db.Column(db.String(50), nullable=True, index=True)  # Original Assy_# for duplicate checking
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('assembly_categories.category_id'), nullable=False, index=True)
    base_assembly_id = db.Column(db.Integer, db.ForeignKey('standard_assemblies.standard_assembly_id'))
    version = db.Column(db.String(20), nullable=False, default='1.0')
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_template = db.Column(db.Boolean, default=False)  # True if this is the current template version
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = db.relationship('AssemblyCategory', backref='standard_assemblies')
    components = db.relationship('StandardAssemblyComponent', backref='standard_assembly', cascade='all, delete-orphan')
    versions = db.relationship('AssemblyVersion', backref='standard_assembly', cascade='all, delete-orphan')
    base_assembly = db.relationship('StandardAssembly', remote_side=[standard_assembly_id], backref='derived_versions')
    
    @property
    def total_cost(self):
        """Calculate total cost of all components in this standard assembly"""
        return sum(component.total_price for component in self.components)
    
    @property
    def component_count(self):
        """Count of components in this assembly"""
        return len(self.components)
    
    def get_version_history(self):
        """Get all versions of this assembly (including base and derived)"""
        if self.base_assembly_id:
            # This is a derived version, get all versions of the base
            base = StandardAssembly.query.get(self.base_assembly_id)
            if base:
                # Get base assembly plus all its derived versions
                versions = [base] + StandardAssembly.query.filter_by(base_assembly_id=base.standard_assembly_id).all()
                return sorted(versions, key=lambda x: x.created_at, reverse=True)
            else:
                # Base assembly doesn't exist, treat this as the only version
                return [self]
        else:
            # This is a base assembly, get itself plus all derived versions
            versions = [self] + StandardAssembly.query.filter_by(base_assembly_id=self.standard_assembly_id).all()
            return sorted(versions, key=lambda x: x.created_at, reverse=True)
    
    def create_new_version(self, version_notes=''):
        """Create a new version of this standard assembly"""
        # Find the next version number
        existing_versions = self.get_version_history()
        version_numbers = [float(v.version) for v in existing_versions if v.version.replace('.', '').isdigit()]
        next_version = max(version_numbers) + 0.1 if version_numbers else 1.1
        
        # Create new version
        new_version = StandardAssembly(
            name=self.name,
            description=self.description,
            category_id=self.category_id,
            base_assembly_id=self.base_assembly_id or self.standard_assembly_id,
            version=f"{next_version:.1f}",
            is_active=True,
            is_template=True,  # New version becomes the template
            created_by=self.created_by
        )
        
        # Mark current version as not template
        self.is_template = False
        
        # Copy components
        for component in self.components:
            new_component = StandardAssemblyComponent(
                part_id=component.part_id,
                quantity=component.quantity,
                unit_of_measure=component.unit_of_measure,
                notes=component.notes,
                sort_order=component.sort_order
            )
            new_version.components.append(new_component)
        
        # Add and flush the new version to get the ID
        db.session.add(new_version)
        db.session.flush()  # This assigns the standard_assembly_id without committing
        
        # Create version history record
        version_record = AssemblyVersion(
            standard_assembly_id=new_version.standard_assembly_id,
            version_number=new_version.version,
            notes=version_notes,
            created_by=self.created_by
        )
        
        db.session.add(version_record)
        
        return new_version
    
    def __repr__(self):
        return f'<StandardAssembly {self.name} v{self.version}>'

class StandardAssemblyComponent(db.Model):
    """Parts/components within each standard assembly"""
    __tablename__ = 'standard_assembly_components'
    
    component_id = db.Column(db.Integer, primary_key=True)
    standard_assembly_id = db.Column(db.Integer, db.ForeignKey('standard_assemblies.standard_assembly_id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False, default=1.000)
    unit_of_measure = db.Column(db.String(20), default='EA')
    notes = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = db.relationship('Parts', backref='standard_assembly_components')
    
    @property
    def unit_price(self):
        """Get current price from the part"""
        return self.part.current_price if self.part else 0.0
    
    @property
    def total_price(self):
        """Calculate total price for this quantity"""
        return self.unit_price * float(self.quantity)
    
    @property
    def part_number(self):
        """Get part number from the linked part"""
        return self.part.part_number if self.part else 'Unknown'
        
    @property
    def description(self):
        """Get description from the linked part, or use component notes"""
        return self.notes or (self.part.description if self.part else 'No description')
    
    @property
    def component_name(self):
        """Get component display name"""
        return self.part.description or self.part.part_number
    
    def __repr__(self):
        return f'<StandardAssemblyComponent {self.part.part_number} x{self.quantity}>'

class AssemblyVersion(db.Model):
    """Version history tracking for standard assemblies"""
    __tablename__ = 'assembly_versions'
    
    version_id = db.Column(db.Integer, primary_key=True)
    standard_assembly_id = db.Column(db.Integer, db.ForeignKey('standard_assemblies.standard_assembly_id'), nullable=False)
    version_number = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AssemblyVersion {self.version_number}>'

class AssemblyCategory(db.Model):
    """Manageable categories for standard assemblies"""
    __tablename__ = 'assembly_categories'
    
    category_id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AssemblyCategory {self.code}: {self.name}>'
    
    @classmethod
    def get_active_categories(cls):
        """Get all active categories ordered by sort_order then name"""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.name).all()
    
    @classmethod
    def get_all_categories(cls):
        """Get all categories ordered by sort_order then name"""
        return cls.query.order_by(cls.sort_order, cls.name).all()
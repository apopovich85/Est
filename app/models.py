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
    is_active = db.Column(db.Boolean, default=True)
    revision = db.Column(db.String(50), default='')
    remarks = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimates = db.relationship('Estimate', backref='project', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.project_name}>'
    
    def total_value(self):
        return sum(estimate.calculated_total for estimate in self.estimates if not estimate.is_optional)

    def total_project_hours(self):
        """Calculate total hours across all estimates in project (excluding optional)"""
        return sum(estimate.total_hours for estimate in self.estimates if not estimate.is_optional)

    def total_project_engineering_hours(self):
        """Calculate total engineering hours across all estimates in project (excluding optional)"""
        return sum(estimate.total_engineering_hours for estimate in self.estimates if not estimate.is_optional)

    def total_project_panel_shop_hours(self):
        """Calculate total panel shop hours across all estimates in project (excluding optional)"""
        return sum(estimate.total_panel_shop_hours for estimate in self.estimates if not estimate.is_optional)

    def total_project_machine_assembly_hours(self):
        """Calculate total machine assembly hours across all estimates in project (excluding optional)"""
        return sum(estimate.total_machine_assembly_hours for estimate in self.estimates if not estimate.is_optional)

    def total_project_labor_cost(self):
        """Calculate total labor cost across all estimates in project (excluding optional)"""
        return sum(estimate.total_labor_cost for estimate in self.estimates if not estimate.is_optional)

    def total_project_material_cost(self):
        """Calculate total material cost across all estimates in project (excluding optional)"""
        return sum(estimate.calculated_total for estimate in self.estimates if not estimate.is_optional)

    def total_project_grand_total(self):
        """Calculate total project value including materials and labor (excluding optional)"""
        return sum(estimate.grand_total for estimate in self.estimates if not estimate.is_optional)

class Estimate(db.Model):
    __tablename__ = 'estimates'

    estimate_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
    estimate_number = db.Column(db.String(100), unique=True, nullable=False)
    estimate_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    total_value = db.Column(db.Numeric(12, 2), default=0.00)
    sort_order = db.Column(db.Integer, default=0)
    revision_number = db.Column(db.Integer, default=0)
    is_optional = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Labor rate snapshot (preserves rates used when estimate was created)
    engineering_rate = db.Column(db.Numeric(8, 2), default=145.00)
    panel_shop_rate = db.Column(db.Numeric(8, 2), default=125.00)
    machine_assembly_rate = db.Column(db.Numeric(8, 2), default=125.00)
    rate_snapshot_date = db.Column(db.Date)
    
    # Simple labor hours tracking at estimate level
    engineering_hours = db.Column(db.Numeric(8, 2), default=0.0)
    panel_shop_hours = db.Column(db.Numeric(8, 2), default=0.0)
    machine_assembly_hours = db.Column(db.Numeric(8, 2), default=0.0)
    
    # Relationships
    assemblies = db.relationship('Assembly', backref='estimate', cascade='all, delete-orphan')
    individual_components = db.relationship('EstimateComponent', backref='estimate', cascade='all, delete-orphan')
    revisions = db.relationship('EstimateRevision', backref='estimate', cascade='all, delete-orphan')
    
    @property
    def calculated_total(self):
        """Calculate the total value of all assemblies and individual components in this estimate"""
        assembly_total = sum(assembly.calculated_total for assembly in self.assemblies)
        component_total = sum(comp.total_price for comp in self.individual_components)
        return assembly_total + component_total
    
    @property
    def total_engineering_hours(self):
        """Get engineering hours from the estimate level field"""
        return float(self.engineering_hours or 0)
    
    @property
    def total_panel_shop_hours(self):
        """Get panel shop hours from the estimate level field"""
        return float(self.panel_shop_hours or 0)
    
    @property
    def total_machine_assembly_hours(self):
        """Get machine assembly hours from the estimate level field"""
        return float(self.machine_assembly_hours or 0)
    
    @property
    def total_hours(self):
        """Calculate total hours across all labor types and assemblies"""
        return self.total_engineering_hours + self.total_panel_shop_hours + self.total_machine_assembly_hours
    
    @property
    def total_engineering_cost(self):
        """Calculate total engineering cost from estimate hours and rate"""
        return float(self.engineering_hours or 0) * float(self.engineering_rate or 145.0)
    
    @property
    def total_panel_shop_cost(self):
        """Calculate total panel shop cost from estimate hours and rate"""
        return float(self.panel_shop_hours or 0) * float(self.panel_shop_rate or 125.0)
    
    @property
    def total_machine_assembly_cost(self):
        """Calculate total machine assembly cost from estimate hours and rate"""
        return float(self.machine_assembly_hours or 0) * float(self.machine_assembly_rate or 125.0)
    
    @property
    def total_labor_cost(self):
        """Calculate total labor cost across all assemblies"""
        return self.total_engineering_cost + self.total_panel_shop_cost + self.total_machine_assembly_cost
    
    @property
    def grand_total(self):
        """Calculate grand total including materials and labor"""
        return self.calculated_total + self.total_labor_cost
    
    def create_revision(self, changes_summary=None, detailed_changes=None, created_by=None):
        """Create a new revision of this estimate"""
        # Increment revision number
        self.revision_number += 1
        
        # Create revision history record
        revision = EstimateRevision(
            estimate_id=self.estimate_id,
            revision_number=self.revision_number,
            changes_summary=changes_summary,
            detailed_changes=detailed_changes,
            created_by=created_by
        )
        
        db.session.add(revision)
        self.updated_at = datetime.utcnow()
        
        return revision
    
    def get_revision_history(self):
        """Get all revisions for this estimate"""
        return EstimateRevision.query.filter_by(estimate_id=self.estimate_id)\
            .order_by(EstimateRevision.revision_number.desc()).all()
    
    @property
    def current_revision_summary(self):
        """Get the most recent revision summary"""
        latest_revision = EstimateRevision.query.filter_by(
            estimate_id=self.estimate_id, 
            revision_number=self.revision_number
        ).first()
        return latest_revision.changes_summary if latest_revision else None
    
    def __repr__(self):
        return f'<Estimate {self.estimate_number} Rev.{self.revision_number}>'

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
    
    
    # Relationships - now uses AssemblyPart instead of Component
    assembly_parts = db.relationship('AssemblyPart', backref='assembly', cascade='all, delete-orphan')
    
    @property
    def calculated_total(self):
        """Calculate the total value of all parts in this assembly"""
        return sum(ap.total_price for ap in self.assembly_parts)
    
    @property
    def total_labor_cost(self):
        """Labor cost for assembly - now always 0 since labor is tracked at estimate level"""
        return 0.0
    
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

class VFDType(db.Model):
    """VFD type lookup table for drive selection"""
    __tablename__ = 't_vfdtype'
    
    vfd_type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), nullable=False, unique=True)
    manufacturer = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, index=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    motors = db.relationship('Motor', backref='vfd_type')
    
    @classmethod
    def get_active_types(cls):
        """Get all active VFD types ordered by sort_order then name"""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.type_name).all()
    
    def __repr__(self):
        return f'<VFDType {self.type_name}>'

class NECAmpTable(db.Model):
    """NEC motor full load current lookup table"""
    __tablename__ = 't_necamptable'
    
    nec_amp_id = db.Column(db.Integer, primary_key=True)
    hp = db.Column(db.Numeric(6, 2), nullable=False, unique=True, index=True)
    voltage_115 = db.Column(db.Numeric(8, 2))
    voltage_200 = db.Column(db.Numeric(8, 2))
    voltage_208 = db.Column(db.Numeric(8, 2))
    voltage_230 = db.Column(db.Numeric(8, 2))
    voltage_460 = db.Column(db.Numeric(8, 2))
    voltage_575 = db.Column(db.Numeric(8, 2))
    voltage_2300 = db.Column(db.Numeric(8, 2))
    
    @classmethod
    def get_motor_amps(cls, hp, voltage):
        """Get motor amps from NEC table for given HP and voltage"""
        record = cls.query.filter_by(hp=hp).first()
        if not record:
            return None
            
        voltage_field = f'voltage_{int(voltage)}'
        if hasattr(record, voltage_field):
            amps = getattr(record, voltage_field, None)
            return float(amps) if amps is not None else None
        return None
    
    def __repr__(self):
        return f'<NECAmpTable {self.hp}HP>'

class TechData(db.Model):
    """Technical specifications for parts (VFDs, etc.)"""
    __tablename__ = 't_techdata'

    tech_data_id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=False, index=True)
    heat_loss_w = db.Column(db.Numeric(10, 2))  # Heat Loss in Watts
    width_in = db.Column(db.Numeric(8, 3))      # Width in inches
    height_in = db.Column(db.Numeric(8, 3))     # Height in inches
    length_in = db.Column(db.Numeric(8, 3))     # Length in inches
    frame_size = db.Column(db.Integer)          # Frame size for calculations
    input_current = db.Column(db.Numeric(8, 3)) # Input current for VFDs (deprecated - use ND/HD)
    input_current_nd = db.Column(db.Numeric(8, 3)) # Normal Duty input current for VFDs
    input_current_hd = db.Column(db.Numeric(8, 3)) # Heavy Duty input current for VFDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    part = db.relationship('Parts', backref=db.backref('tech_data', uselist=False))
    
    def __repr__(self):
        return f'<TechData for Part {self.part_id}>'

class Motor(db.Model):
    """Motors and loads associated with projects"""
    __tablename__ = 't_motors'
    
    motor_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False, index=True)
    load_type = db.Column(db.String(20), nullable=False, default='motor')  # 'motor' or 'load'
    motor_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(100))
    encl_type = db.Column(db.String(50))
    frame = db.Column(db.String(50))
    additional_notes = db.Column(db.Text)
    hp = db.Column(db.Numeric(8, 2), nullable=True)  # Only for motors
    speed_range = db.Column(db.String(50))
    voltage = db.Column(db.Numeric(8, 2), nullable=False)  # 115, 200, 208, 230, 460, 575, 2300
    qty = db.Column(db.Integer, nullable=False, default=1)  # Changed to Integer for whole numbers
    overload_percentage = db.Column(db.Numeric(5, 3), nullable=True, default=1.15)  # Only for motors
    continuous_load = db.Column(db.Boolean, default=True, nullable=False)  # NEC continuous load flag
    vfd_type_id = db.Column(db.Integer, db.ForeignKey('t_vfdtype.vfd_type_id'), nullable=True)
    
    # Load-specific fields
    power_rating = db.Column(db.Numeric(10, 3), nullable=True)  # Power in kVA or Amps for loads
    power_unit = db.Column(db.String(10), default='kVA')  # 'kVA' or 'Amps'
    phase_config = db.Column(db.String(10), default='three')  # 'single' or 'three'
    
    # Override options
    nec_amps_override = db.Column(db.Boolean, default=False)
    manual_amps = db.Column(db.Numeric(8, 3))  # Manual amp entry when overridden
    vfd_override = db.Column(db.Boolean, default=False)
    selected_vfd_part_id = db.Column(db.Integer, db.ForeignKey('parts.part_id'), nullable=True)
    duty_type = db.Column(db.String(2), default='ND')  # 'ND' for Normal Duty, 'HD' for Heavy Duty
    
    # Metadata
    sort_order = db.Column(db.Integer, default=0)
    revision_number = db.Column(db.String(20), default='0.0')
    revision_type = db.Column(db.String(20), default='major')  # 'major', 'minor', 'overwrite'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref=db.backref('motors', cascade='all, delete-orphan'))
    selected_vfd = db.relationship('Parts', backref='motor_selections')
    revisions = db.relationship('MotorRevision', backref='motor', cascade='all, delete-orphan', order_by='MotorRevision.revision_number.desc()')
    
    @property
    def motor_amps(self):
        """Get motor amps - either from NEC table, manual override, or load calculation"""
        if self.nec_amps_override and self.manual_amps:
            return float(self.manual_amps)
        elif self.load_type == 'load':
            return self.calculated_load_amps
        else:
            # Motor type - use NEC table
            if not self.hp:
                return 0.0
            nec_amps = NECAmpTable.get_motor_amps(self.hp, self.voltage)
            return float(nec_amps) if nec_amps else 0.0
    
    @property
    def calculated_load_amps(self):
        """Calculate amps for loads based on power_rating, power_unit, voltage, and phase"""
        if not self.power_rating or not self.voltage:
            return 0.0
            
        power = float(self.power_rating)
        voltage = float(self.voltage)
        
        if self.power_unit == 'Amps':
            # Power is already in amps
            return power
        elif self.power_unit == 'kVA':
            # Convert kVA to amps
            if self.phase_config == 'three':
                # Three-phase: Amps = (kVA × 1000) / (Voltage × √3)
                import math
                return (power * 1000) / (voltage * math.sqrt(3))
            else:
                # Single-phase: Amps = (kVA × 1000) / Voltage
                return (power * 1000) / voltage
        
        return 0.0
    
    @property
    def load_amps_per_phase(self):
        """For single-phase loads balanced across 3 phases, return amps per phase"""
        if self.load_type == 'load' and self.phase_config == 'single':
            # Single-phase load balanced across 3 phases
            return self.calculated_load_amps / 3
        else:
            # Three-phase load or motor
            return self.calculated_load_amps
    
    @property
    def total_amps(self):
        """Calculate total amps: qty * motor_amps"""
        return float(self.qty) * self.motor_amps
    
    @property
    def drive_required_current(self):
        """Calculate required current for VFD: motor_amps * overload_percentage"""
        return self.motor_amps * float(self.overload_percentage)
    
    @property
    def recommended_vfd(self):
        """Get recommended VFD part based on required current and VFD type"""
        if self.vfd_override and self.selected_vfd:
            return self.selected_vfd
            
        if not self.vfd_type_id:
            return None
            
        # Find VFDs that match the type and have sufficient rating
        from sqlalchemy import and_, cast, Float
        
        vfd_query = db.session.query(Parts)\
            .filter(and_(
                Parts.description.contains(self.vfd_type.type_name),
                cast(Parts.rating, Float) >= self.drive_required_current
            ))\
            .order_by(cast(Parts.rating, Float).asc())
        
        return vfd_query.first()  # Return the smallest sufficient VFD
    
    @property
    def vfd_input_current(self):
        """Get VFD input current from tech data based on duty type"""
        vfd = self.recommended_vfd
        if vfd and vfd.tech_data:
            # Use duty type to determine which input current to use
            if self.duty_type == 'HD' and vfd.tech_data.input_current_hd:
                return float(vfd.tech_data.input_current_hd)
            elif self.duty_type == 'ND' and vfd.tech_data.input_current_nd:
                return float(vfd.tech_data.input_current_nd)
            # Fallback to legacy input_current if ND/HD not available
            elif vfd.tech_data.input_current:
                return float(vfd.tech_data.input_current)
        return 0.0
    
    @property
    def total_vfd_input_current(self):
        """Calculate total VFD input current: input_current * qty"""
        return self.vfd_input_current * float(self.qty)
    
    @property
    def vfd_heat_loss(self):
        """Get VFD heat loss from tech data multiplied by quantity"""
        vfd = self.recommended_vfd
        if vfd and vfd.tech_data:
            return float(vfd.tech_data.heat_loss_w or 0.0) * float(self.qty)
        return 0.0
    
    @property
    def vfd_width(self):
        """Get VFD width from tech data"""
        vfd = self.recommended_vfd
        if vfd and vfd.tech_data:
            return float(vfd.tech_data.width_in or 0.0)
        return 0.0
    
    @property
    def total_width(self):
        """Calculate total width including frame spacing"""
        vfd = self.recommended_vfd
        if not vfd or not vfd.tech_data:
            return 0.0
            
        width = self.vfd_width
        frame_size = int(vfd.tech_data.frame_size or 0)
        
        # Frame spacing logic from Excel: IF(frame>=4, 4.5+width, IF(frame=3, 4+width, IF(frame=2, 3.625+width)))
        if frame_size >= 4:
            spacing = 4.5
        elif frame_size == 3:
            spacing = 4.0
        elif frame_size == 2:
            spacing = 3.625
        else:
            spacing = 0.0
            
        return (spacing + width) * float(self.qty)
    
    def get_vfd_options(self):
        """Get all VFD options for the selected type that meet current requirements"""
        if not self.vfd_type_id:
            return []
            
        from sqlalchemy import and_, cast, Float
        
        return db.session.query(Parts)\
            .filter(and_(
                Parts.description.contains(self.vfd_type.type_name),
                cast(Parts.rating, Float) >= self.drive_required_current
            ))\
            .order_by(cast(Parts.rating, Float).asc())\
            .all()
    
    def detect_changes(self, new_data):
        """
        Detect what fields changed and suggest revision type
        Returns: (changed_fields, suggested_revision_type)
        """
        # Define field significance for revision suggestion
        MAJOR_FIELDS = {'hp', 'voltage', 'vfd_type_id', 'load_type', 'power_rating', 'phase_config', 'duty_type'}
        MINOR_FIELDS = {'qty', 'location', 'motor_name', 'overload_percentage', 'continuous_load',
                       'speed_range', 'encl_type', 'frame', 'power_unit', 'nec_amps_override',
                       'manual_amps', 'vfd_override', 'selected_vfd_part_id'}
        TRIVIAL_FIELDS = {'additional_notes', 'sort_order'}

        changed_fields = {}

        for field in MAJOR_FIELDS | MINOR_FIELDS | TRIVIAL_FIELDS:
            old_value = getattr(self, field, None)
            new_value = new_data.get(field)

            # Skip if value unchanged
            if old_value == new_value:
                continue

            # Convert to comparable types
            if old_value is not None and new_value is not None:
                try:
                    if isinstance(old_value, (int, float)):
                        new_value = type(old_value)(new_value)
                    if old_value == new_value:
                        continue
                except:
                    pass

            changed_fields[field] = {'old': old_value, 'new': new_value}

        # Determine suggested revision type
        if any(field in MAJOR_FIELDS for field in changed_fields):
            suggested_type = 'major'
        elif any(field in MINOR_FIELDS for field in changed_fields):
            suggested_type = 'minor'
        else:
            suggested_type = 'overwrite'

        return changed_fields, suggested_type

    def increment_revision(self, revision_type='minor'):
        """
        Increment revision number based on type
        - major: 1.0 -> 2.0
        - minor: 1.0 -> 1.1, 1.1 -> 1.2
        - overwrite: 1.0 -> 1.0 (no change)
        """
        if revision_type == 'overwrite':
            return self.revision_number

        try:
            major, minor = self.revision_number.split('.')
            major, minor = int(major), int(minor)
        except:
            # If parsing fails, start fresh
            major, minor = 0, 0

        if revision_type == 'major':
            major += 1
            minor = 0
        else:  # minor
            minor += 1

        return f"{major}.{minor}"

    def create_revision(self, changed_by='System', change_description='', revision_type='minor', fields_changed=None):
        """Create a snapshot of the current motor state"""
        revision = MotorRevision(
            motor_id=self.motor_id,
            revision_number=self.revision_number,
            revision_type=revision_type,
            fields_changed=str(fields_changed) if fields_changed else None,
            load_type=self.load_type,
            motor_name=self.motor_name,
            location=self.location,
            encl_type=self.encl_type,
            frame=self.frame,
            additional_notes=self.additional_notes,
            hp=self.hp,
            speed_range=self.speed_range,
            voltage=self.voltage,
            qty=self.qty,
            overload_percentage=self.overload_percentage,
            continuous_load=self.continuous_load,
            vfd_type_id=self.vfd_type_id,
            power_rating=self.power_rating,
            power_unit=self.power_unit,
            phase_config=self.phase_config,
            nec_amps_override=self.nec_amps_override,
            manual_amps=self.manual_amps,
            vfd_override=self.vfd_override,
            selected_vfd_part_id=self.selected_vfd_part_id,
            duty_type=self.duty_type,
            changed_by=changed_by,
            change_description=change_description
        )
        db.session.add(revision)
        return revision

    def revert_to_revision(self, revision_number):
        """Revert motor to a previous revision"""
        revision = MotorRevision.query.filter_by(
            motor_id=self.motor_id,
            revision_number=revision_number
        ).first()

        if not revision:
            raise ValueError(f"Revision {revision_number} not found")

        # Save current state before reverting
        self.create_revision(
            changed_by='System',
            change_description=f'Reverted to revision {revision_number}'
        )

        # Update motor fields from revision
        self.load_type = revision.load_type
        self.motor_name = revision.motor_name
        self.location = revision.location
        self.encl_type = revision.encl_type
        self.frame = revision.frame
        self.additional_notes = revision.additional_notes
        self.hp = revision.hp
        self.speed_range = revision.speed_range
        self.voltage = revision.voltage
        self.qty = revision.qty
        self.overload_percentage = revision.overload_percentage
        self.continuous_load = revision.continuous_load
        self.vfd_type_id = revision.vfd_type_id
        self.power_rating = revision.power_rating
        self.power_unit = revision.power_unit
        self.phase_config = revision.phase_config
        self.nec_amps_override = revision.nec_amps_override
        self.manual_amps = revision.manual_amps
        self.vfd_override = revision.vfd_override
        self.selected_vfd_part_id = revision.selected_vfd_part_id
        self.duty_type = revision.duty_type

        # Update revision number and metadata
        self.revision_number = self.increment_revision('major')
        self.revision_type = 'major'
        self.updated_at = datetime.utcnow()

    @property
    def revision_display(self):
        """Format revision for display"""
        return f"v{self.revision_number}"

    def __repr__(self):
        return f'<Motor {self.motor_name} ({self.hp}HP) Rev.{self.revision_number}>'


class MotorRevision(db.Model):
    """Track revision history for motors/loads"""
    __tablename__ = 'motor_revisions'

    revision_id = db.Column(db.Integer, primary_key=True)
    motor_id = db.Column(db.Integer, db.ForeignKey('t_motors.motor_id'), nullable=False)
    revision_number = db.Column(db.String(20), nullable=False)
    revision_type = db.Column(db.String(20), default='major')  # 'major', 'minor', 'overwrite'
    fields_changed = db.Column(db.Text)  # JSON string of changed fields

    # Snapshot of all motor fields at time of revision
    load_type = db.Column(db.String(20), nullable=False)
    motor_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(100))
    encl_type = db.Column(db.String(50))
    frame = db.Column(db.String(50))
    additional_notes = db.Column(db.Text)
    hp = db.Column(db.Numeric(8, 2))
    speed_range = db.Column(db.String(50))
    voltage = db.Column(db.Numeric(8, 2), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    overload_percentage = db.Column(db.Numeric(5, 3))
    continuous_load = db.Column(db.Boolean, nullable=False)
    vfd_type_id = db.Column(db.Integer)

    # Load-specific fields
    power_rating = db.Column(db.Numeric(10, 3))
    power_unit = db.Column(db.String(10))
    phase_config = db.Column(db.String(10))

    # Override options
    nec_amps_override = db.Column(db.Boolean)
    manual_amps = db.Column(db.Numeric(8, 3))
    vfd_override = db.Column(db.Boolean)
    selected_vfd_part_id = db.Column(db.Integer)
    duty_type = db.Column(db.String(2))  # 'ND' for Normal Duty, 'HD' for Heavy Duty

    # Metadata
    changed_by = db.Column(db.String(100))
    change_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def revision_display(self):
        """Format revision for display"""
        type_icon = {'major': '🔴', 'minor': '🟡', 'overwrite': '🔵'}.get(self.revision_type, '')
        return f"v{self.revision_number} {type_icon}"

    def __repr__(self):
        return f'<MotorRevision {self.motor_id} Rev.{self.revision_number} ({self.revision_type})>'


class EstimateRevision(db.Model):
    """Track revision history for estimates"""
    __tablename__ = 'estimate_revisions'
    
    revision_id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey('estimates.estimate_id'), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False)
    changes_summary = db.Column(db.Text)
    detailed_changes = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('estimate_id', 'revision_number'),)
    
    def __repr__(self):
        return f'<EstimateRevision {self.estimate_id} Rev.{self.revision_number}>'
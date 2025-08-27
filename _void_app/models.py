from app import db
from datetime import datetime
from sqlalchemy import event

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
        return sum(estimate.total_value or 0 for estimate in self.estimates)

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
    
    # Relationships
    assemblies = db.relationship('Assembly', backref='estimate', cascade='all, delete-orphan')
    
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
    
    # Relationships
    components = db.relationship('Component', backref='assembly', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Assembly {self.assembly_name}>'

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
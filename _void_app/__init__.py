from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import os

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database/estimates.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.projects import bp as projects_bp
    from app.routes.estimates import bp as estimates_bp
    from app.routes.assemblies import bp as assemblies_bp
    from app.routes.components import bp as components_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(estimates_bp, url_prefix='/estimates')
    app.register_blueprint(assemblies_bp, url_prefix='/assemblies')
    app.register_blueprint(components_bp, url_prefix='/components')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app
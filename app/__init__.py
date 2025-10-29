from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
import os

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()

# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite"""
    if 'sqlite' in str(dbapi_conn):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Define a consistent absolute path for the database file in project root
    database_path = os.path.join(app.root_path, '..', 'estimates.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Add custom template filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Format a number as currency with commas and 2 decimal places"""
        if value is None:
            return "$0.00"
        try:
            return "${:,.2f}".format(float(value))
        except (ValueError, TypeError):
            return "$0.00"

    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.projects import bp as projects_bp
    from app.routes.estimates import bp as estimates_bp
    from app.routes.assemblies import bp as assemblies_bp
    from app.routes.components import bp as components_bp
    from app.routes.parts import bp as parts_bp
    # Standard assemblies blueprint
    from app.routes.standard_assemblies import bp as standard_assemblies_bp
    # Categories blueprint
    from app.routes.categories import bp as categories_bp
    # Labor rates blueprint
    from app.routes.labor_rates import bp as labor_rates_bp
    # Motors blueprint
    from app.routes.motors import bp as motors_bp
    # Operator desk blueprint
    from app.routes.operator_desk import bp as operator_desk_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(estimates_bp, url_prefix='/estimates')
    app.register_blueprint(assemblies_bp, url_prefix='/assemblies')
    app.register_blueprint(components_bp, url_prefix='/components')
    app.register_blueprint(parts_bp, url_prefix='/parts')
    app.register_blueprint(standard_assemblies_bp, url_prefix='/standard_assemblies')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(labor_rates_bp, url_prefix='/labor-rates')
    app.register_blueprint(motors_bp)
    app.register_blueprint(operator_desk_bp, url_prefix='/operator-desk')

    # Create tables
    with app.app_context():
        # Create tables (database file will be created automatically in project root)
        db.create_all()

    return app


#from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
#from flask_wtf.csrf import CSRFProtect

#db = SQLAlchemy()
#csrf = CSRFProtect()

#def create_app():
 #   app = Flask(__name__)
  #  
    # Simple config to avoid OneDrive issues
   # from pathlib import Path
    #project_root = Path(__file__).parent.parent
    #db_file = project_root / 'estimates.db'
    
   # app.config['SECRET_KEY'] = 'dev-secret-key'
    #app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
    #app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    #db.init_app(app)
    #csrf.init_app(app)
    
    # Register blueprints
    #try:
     #   from app.routes.main import bp as main_bp
      #  app.register_blueprint(main_bp)
    #except ImportError:
     #   @app.route('/')
      #  def home():
       #     return '<h1>App Started - Database Fixed!</h1>'
    
    #return app
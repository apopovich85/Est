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

    # Define a consistent absolute path for the database file in project root
    database_path = os.path.join(app.root_path, '..', 'estimates.db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
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
    from app.routes.parts import bp as parts_bp
    # Standard assemblies blueprint
    from app.routes.standard_assemblies import bp as standard_assemblies_bp
    # Categories blueprint
    from app.routes.categories import bp as categories_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(estimates_bp, url_prefix='/estimates')
    app.register_blueprint(assemblies_bp, url_prefix='/assemblies')
    app.register_blueprint(components_bp, url_prefix='/components')
    app.register_blueprint(parts_bp, url_prefix='/parts')
    app.register_blueprint(standard_assemblies_bp, url_prefix='/standard_assemblies')
    app.register_blueprint(categories_bp, url_prefix='/categories')

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
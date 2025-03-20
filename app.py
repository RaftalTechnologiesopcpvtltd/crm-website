import os
import logging
from datetime import datetime
from flask import Flask, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from sqlalchemy.orm import DeclarativeBase
from werkzeug.exceptions import HTTPException

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configure the app
    app.secret_key = os.environ.get("SESSION_SECRET")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///employee_management.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'accounts.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    # Register blueprints
    with app.app_context():
        from blueprints.accounts.routes import accounts_bp
        from blueprints.hr.routes import hr_bp
        from blueprints.project_management.routes import project_bp
        from blueprints.accounting import accounting_bp
        
        app.register_blueprint(accounts_bp)
        app.register_blueprint(hr_bp)
        app.register_blueprint(project_bp)
        app.register_blueprint(accounting_bp)
        
        # Make sure the models are imported and tables created
        import models
        import models_accounting
        
        db.create_all()
        
        # Create a test/admin user if not exists
        from models import User
        from werkzeug.security import generate_password_hash
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info('Admin user created')
            
        # Initialize accounting data
        from blueprints.accounting.routes import initialize_accounting
        initialize_accounting()
    
    # Template filters
    @app.template_filter('formatdate')
    def format_date(value, format='%Y-%m-%d'):
        if value:
            return value.strftime(format)
        return ""
    
    @app.template_filter('time_remaining')
    def time_remaining_filter(due_date, start_date=None):
        from utils import get_time_remaining
        return get_time_remaining(due_date, start_date)
        
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        from utils import format_currency
        return format_currency(value)
    
    # Context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    # Error handlers
    @app.errorhandler(HTTPException)
    def handle_exception(e):
        return f"""
        <h1>Error {e.code}</h1>
        <p>{e.name}: {e.description}</p>
        <a href="{url_for('project_management.dashboard')}">Return to Dashboard</a>
        """, e.code
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    return app

# Import this after the app factory to avoid circular imports
from flask import render_template

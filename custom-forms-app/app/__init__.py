"""
Factory pattern pour créer l'application Flask
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config

# Initialisation des extensions Flask
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name=None):
    """
    Factory function pour créer et configurer l'application Flask
    
    Args:
        config_name (str): Nom de la configuration à utiliser
        
    Returns:
        Flask: Instance de l'application configurée
    """
    app = Flask(__name__)
    
    # Déterminer la configuration à utiliser
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Charger la configuration
    app.config.from_object(config[config_name])
    
    # Initialiser les extensions avec l'application
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configuration de Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'info'
    
    # Fonction de chargement de l'utilisateur pour Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Créer le dossier d'upload s'il n'existe pas
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Enregistrement des blueprints (routes)
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.forms import forms_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(forms_bp, url_prefix='/forms')
    
    # Enregistrer le blueprint admin seulement si on peut l'importer
    try:
        from app.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
    except ImportError:
        # Si l'import échoue, on continue sans le blueprint admin
        pass
    
    # Enregistrement du blueprint api
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Création des tables de base de données
    with app.app_context():
        db.create_all()
    
    return app

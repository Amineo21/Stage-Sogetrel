# Custom Forms Flask Application

This is a Flask application for creating and managing custom forms, including features for file uploads, signatures, geolocation, and admin management.

## Setup

1.  **Clone the repository:**
    \`\`\`bash
    git clone <repository_url>
    cd custom-forms-app
    \`\`\`

2.  **Create a virtual environment and activate it:**
    \`\`\`bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    \`\`\`

3.  **Install dependencies:**
    \`\`\`bash
    pip install -r requirements.txt
    \`\`\`

4.  **Set up environment variables:**
    Create a `.env` file in the root directory based on `.env.example`.

    ```dotenv
    FLASK_ENV=development
    SECRET_KEY=your_super_secret_key_for_development
    DATABASE_URL=sqlite:///forms.db
    # MAIL_SERVER=smtp.mailtrap.io
    # MAIL_PORT=2525
    # MAIL_USE_TLS=True
    # MAIL_USERNAME=your_mailtrap_username
    # MAIL_PASSWORD=your_mailtrap_password
    # MAIL_DEFAULT_SENDER=no-reply@yourdomain.com
    \`\`\`

5.  **Initialize and migrate the database:**
    \`\`\`bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    \`\`\`

6.  **Create an admin user (optional but recommended for full access):**
    \`\`\`bash
    python scripts/create_admin_users.py
    \`\`\`

7.  **Run the application:**
    \`\`\`bash
    python run.py
    \`\`\`

    The application will be accessible at `http://127.0.0.1:5000/`.

## Features

*   **User Authentication:** Register, login, logout.
*   **Form Creation:** Dynamically build forms with various field types.
*   **Form Filling:** Users can fill out forms.
*   **File Uploads:** Support for file attachments in forms.
*   **Digital Signatures:** Capture signatures directly in forms.
*   **Geolocation:** Record user's location when submitting forms.
*   **Admin Panel:**
    *   Dashboard with statistics.
    *   User management (create, edit, activate/deactivate, change role, delete).
    *   Form management (activate/deactivate, delete).
*   **Data Export:** Export form responses to Excel, including images and signatures.
*   **Email Notifications:** Send email notifications on form submission.

## Project Structure

\`\`\`
.
├── app/
│   ├── __init__.py             # Flask app creation and configuration
│   ├── forms.py                # WTForms for user and admin forms
│   ├── models.py               # SQLAlchemy models for database
│   ├── routes/
│   │   ├── __init__.py         # Blueprint registration
│   │   ├── admin.py            # Admin-specific routes
│   │   ├── api.py              # API routes for form builder, etc.
│   │   ├── auth.py             # Authentication routes
│   │   ├── forms.py            # Form creation, filling, and management routes
│   │   └── main.py             # Main application routes (dashboard, index)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Custom CSS
│   │   └── js/
│   │       ├── form-builder.js # JavaScript for dynamic form building
│   │       ├── geolocation.js  # JavaScript for geolocation capture
│   │       └── signature.js    # JavaScript for signature pad
│   └── templates/
│       ├── admin/              # Admin panel HTML templates
│       │   ├── create_user.html
│       │   ├── dashboard.html
│       │   ├── edit_user.html
│       │   ├── manage_forms.html
│       │   └── manage_users.html
│       ├── auth/               # Authentication HTML templates
│       │   ├── login.html
│       │   └── register.html
│       ├── forms/              # Form-related HTML templates
│       │   ├── create.html
│       │   ├── edit.html
│       │   ├── fill.html
│       │   ├── list.html
│       │   ├── responses.html
│       │   ├── share.html
│       │   └── view.html
│       ├── base.html           # Base template for consistent layout
│       ├── dashboard.html      # User dashboard
│       └── index.html          # Homepage
├── migrations/                 # Alembic migration scripts
├── scripts/
│   ├── add_address_field.py    # Database migration script example
│   ├── add_email_features.py   # Script to add email features to existing forms
│   └── create_admin_users.py   # Script to create initial admin users
├── uploads/                    # Directory for uploaded files (created automatically)
├── venv/                       # Python virtual environment
├── config.py                   # Application configuration
├── .env.example                # Example environment variables
├── run.py                      # Entry point for the Flask application
└── requirements.txt            # Python dependencies
\`\`\`

## Database Migrations

This project uses Flask-Migrate (Alembic) for database migrations.

*   **Initialize migrations (first time only):**
    \`\`\`bash
    flask db init
    \`\`\`
*   **Generate a new migration script:**
    \`\`\`bash
    flask db migrate -m "Description of changes"
    \`\`\`
*   **Apply migrations to the database:**
    \`\`\`bash
    flask db upgrade
    \`\`\`
*   **Revert migrations (use with caution):**
    \`\`\`bash
    flask db downgrade
    \`\`\`

## Contributing

Feel free to fork the repository, make changes, and submit pull requests.

## License

This project is open-source and available under the MIT License.
\`\`\`

```python file="app/__init__.py"
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
    
    # Enregistrer le blueprint admin
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Enregistrement du blueprint api
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Création des tables de base de données
    with app.app_context():
        db.create_all()
    
    return app

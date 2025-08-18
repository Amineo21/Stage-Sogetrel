"""
Modèles de base de données pour l'application de formulaires
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid

from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    """Modèle utilisateur avec gestion des rôles"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # 'user', 'creator', 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relations
    forms = db.relationship('Form', backref='author', lazy='dynamic')
    form_responses = db.relationship('FormResponse', backref='responder', lazy='dynamic')
    email_logs = db.relationship('EmailLog', backref='user', lazy='dynamic')

    # Relations pour le partage de formulaires
    # Formulaires partagés par cet utilisateur
    forms_shared_by_me = db.relationship(
        'FormShare',
        foreign_keys='FormShare.sharer_id',
        backref='sharer',
        lazy='dynamic'
    )
    # Formulaires partagés avec cet utilisateur
    shared_forms_with_me = db.relationship(
        'FormShare',
        foreign_keys='FormShare.shared_with_id',
        backref='shared_with',
        lazy='dynamic'
    )

    def set_password(self, password):
        """Définir le mot de passe hashé"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifier le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Vérifier si l'utilisateur est administrateur"""
        return self.role == 'admin'
    
    def is_creator(self):
        """Vérifier si l'utilisateur peut créer des formulaires"""
        return self.role == 'creator' or self.role == 'admin'
    
    def get_role_display(self):
        """Obtenir le nom d'affichage du rôle"""
        roles = {'user': 'Utilisateur', 'creator': 'Créateur', 'admin': 'Administrateur'}
        return roles.get(self.role, 'Inconnu')
    
    def get_role_badge_class(self):
        """Obtenir la classe CSS pour le badge du rôle"""
        classes = {
            'user': 'badge bg-secondary',
            'creator': 'badge bg-info',
            'admin': 'badge bg-primary'
        }
        return classes.get(self.role, 'badge bg-light')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Form(db.Model):
    """Modèle pour les formulaires personnalisés"""
    
    __tablename__ = 'forms'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    form_data = db.Column(db.JSON, nullable=False)  # Stores JSON structure of the form
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    allow_anonymous = db.Column(db.Boolean, default=False)
    require_login_to_view = db.Column(db.Boolean, default=False)
    send_email_on_submit = db.Column(db.Boolean, default=False)
    email_recipients = db.Column(db.String(500))  # Comma-separated emails

    # Relations
    responses = db.relationship('FormResponse', backref='form', lazy='dynamic')
    shares = db.relationship('FormShare', backref='form', lazy='dynamic')
    
    def __repr__(self):
        return f'<Form {self.title}>'

class FormResponse(db.Model):
    """Modèle pour les réponses aux formulaires"""
    
    __tablename__ = 'form_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Peut être null pour les réponses anonymes
    response_data = db.Column(db.JSON, nullable=False)  # Stores JSON of submitted data
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    geolocation = db.Column(db.String(255))  # e.g., "lat,lon" or "City, Country"
    additional_emails = db.Column(db.String(500))  # Emails entered in the form for specific notifications
    
    # Relations
    files = db.relationship('FormFile', backref='response', lazy='dynamic', cascade='all, delete-orphan')
    email_logs = db.relationship('EmailLog', backref='response', lazy='dynamic')
    
    def get_response_value(self, field_id):
        """Obtenir la valeur d'une réponse spécifique"""
        return self.response_data.get(field_id, '')
    
    def has_signature(self):
        """Vérifier si la réponse a une signature"""
        # Assuming signature is stored in response_data
        return 'signature' in self.response_data
    
    def has_location(self):
        """Vérifier si la réponse a des données de géolocalisation"""
        return self.geolocation is not None
    
    def __repr__(self):
        return f'<FormResponse {self.id} for Form {self.form_id}>'

class FormShare(db.Model):
    """Modèle pour le partage de formulaires entre utilisateurs"""
    
    __tablename__ = 'form_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    sharer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # User who shared the form
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # User with whom the form is shared
    can_edit = db.Column(db.Boolean, default=False)
    can_view_responses = db.Column(db.Boolean, default=False)
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Contrainte d'unicité
    __table_args__ = (db.UniqueConstraint('form_id', 'shared_with_id', name='_form_shared_with_uc'),)
    
    def __repr__(self):
        return f'<FormShare Form:{self.form_id} Sharer:{self.sharer_id} SharedWith:{self.shared_with_id}>'

class FormFile(db.Model):
    """Modèle pour les fichiers uploadés dans les formulaires"""
    
    __tablename__ = 'form_files'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey('form_responses.id'), nullable=True)
    field_id = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def get_file_size_display(self):
        """Obtenir la taille du fichier en format lisible"""
        if not self.file_size:
            return 'Taille inconnue'
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def is_image(self):
        """Vérifier si le fichier est une image"""
        if not self.mime_type:
            return False
        return self.mime_type.startswith('image/')
    
    def __repr__(self):
        return f'<FormFile {self.filename}>'

class EmailLog(db.Model):
    """Modèle pour tracer les envois d'emails"""
    
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who triggered the email (e.g., form submitter)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=True)  # Related form
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body_preview = db.Column(db.Text)  # Short preview of the email body
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))  # e.g., 'sent', 'failed'
    error_message = db.Column(db.Text)  # If status is 'failed'
    
    # Relations
    form = db.relationship('Form', backref='email_logs')
    response = db.relationship('FormResponse', backref='email_logs')
    
    def __repr__(self):
        return f'<EmailLog {self.id} to {self.recipient_email} Status: {self.status}>'

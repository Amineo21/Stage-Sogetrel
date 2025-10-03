from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Répéter le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('S\'inscrire')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Cet email est déjà enregistré.')

class UserCreationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Rôle', choices=[('user', 'Utilisateur'), ('creator', 'Créateur'), ('admin', 'Administrateur')], validators=[DataRequired()])
    is_active = BooleanField('Actif', default=True)
    submit = SubmitField('Créer l\'utilisateur')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Cet email est déjà enregistré.')

class UserEditForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Rôle', choices=[('user', 'Utilisateur'), ('creator', 'Créateur'), ('admin', 'Administrateur')], validators=[DataRequired()])
    is_active = BooleanField('Actif')
    submit = SubmitField('Mettre à jour l\'utilisateur')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Cet email est déjà enregistré.')

class ChangePasswordForm(FlaskForm):
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField(
        'Confirmer le nouveau mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Changer le mot de passe')

class FormBuilderForm(FlaskForm):
    title = StringField('Titre du formulaire', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    is_active = BooleanField('Actif', default=True)
    allow_anonymous = BooleanField('Autoriser les réponses anonymes', default=False)
    require_login_to_view = BooleanField('Exiger une connexion pour voir le formulaire', default=False)
    send_email_on_submit = BooleanField('Envoyer un email après soumission', default=False)
    email_recipients = StringField('Destinataires email (séparés par des virgules)', description='Emails qui recevront une notification après chaque soumission. Laissez vide pour ne pas envoyer.', validators=[Length(max=500)])
    
    # Nouveaux champs pour l'envoi automatique d'emails
    auto_email_enabled = BooleanField('Activer l\'envoi automatique d\'emails', default=False)
    fixed_recipients = TextAreaField('Destinataires fixes', description='Un email par ligne. Ces adresses recevront une copie de chaque soumission.', validators=[Length(max=1000)])
    
    submit = SubmitField('Enregistrer le formulaire')

class ShareForm(FlaskForm):
    email = StringField('Email de l\'utilisateur à partager', validators=[DataRequired(), Email()])
    can_edit = BooleanField('Peut modifier', default=False)
    can_view_responses = BooleanField('Peut voir les réponses', default=False)
    submit = SubmitField('Partager le formulaire')

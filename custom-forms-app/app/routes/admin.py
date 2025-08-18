"""
Routes d'administration pour la gestion des utilisateurs et du système
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps # Import functools
from datetime import datetime, timedelta

from app import db
from app.models import User, Form, FormResponse, EmailLog
from app.forms import UserCreationForm, UserEditForm, ChangePasswordForm # Assurez-vous que ces formulaires existent

# Création du blueprint admin
admin_bp = Blueprint('admin', __name__)

def admin_required(f):
   """Décorateur pour vérifier que l'utilisateur est administrateur"""
   @wraps(f) # Utilisez functools.wraps ici
   @login_required
   def decorated_function(*args, **kwargs):
       if not current_user.is_authenticated or not current_user.is_admin():
           flash('Accès refusé. Vous devez être administrateur.', 'error')
           return redirect(url_for('main.index'))
       return f(*args, **kwargs)
   return decorated_function

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
   """Tableau de bord administrateur"""
   # Statistiques générales
   total_users = User.query.count()
   total_forms = Form.query.count()
   total_responses = FormResponse.query.count()
   active_forms = Form.query.filter_by(is_active=True).count()
   
   # Statistiques par rôle
   admins_count = User.query.filter_by(role='admin').count()
   creators_count = User.query.filter_by(role='creator').count()
   users_count = User.query.filter_by(role='user').count()
   
   # Activité récente (7 derniers jours)
   week_ago = datetime.utcnow() - timedelta(days=7)
   recent_users = User.query.filter(User.created_at >= week_ago).count()
   recent_forms = Form.query.filter(Form.created_at >= week_ago).count()
   recent_responses = FormResponse.query.filter(FormResponse.submitted_at >= week_ago).count()
   
   # Formulaires les plus populaires
   popular_forms = db.session.query(
       Form.title,
       Form.id,
       db.func.count(FormResponse.id).label('response_count')
   ).outerjoin(FormResponse).group_by(Form.id).order_by(
       db.func.count(FormResponse.id).desc()
   ).limit(5).all()
   
   # Utilisateurs récents
   recent_users_list = User.query.order_by(User.created_at.desc()).limit(5).all()
   
   return render_template('admin/dashboard.html',
                        total_users=total_users,
                        total_forms=total_forms,
                        total_responses=total_responses,
                        active_forms=active_forms,
                        admins_count=admins_count,
                        creators_count=creators_count,
                        users_count=users_count,
                        recent_users=recent_users,
                        recent_forms=recent_forms,
                        recent_responses=recent_responses,
                        popular_forms=popular_forms,
                        recent_users_list=recent_users_list)

@admin_bp.route('/users')
@admin_required
def manage_users():
   """Gestion des utilisateurs"""
   page = request.args.get('page', 1, type=int)
   search = request.args.get('search', '', type=str)
   role_filter = request.args.get('role', '', type=str)
   
   # Construction de la requête
   query = User.query
   
   if search:
       query = query.filter(
           (User.username.contains(search)) |
           (User.email.contains(search))
       )
   
   if role_filter:
       query = query.filter(User.role == role_filter)
   
   users = query.order_by(User.created_at.desc()).paginate(
       page=page, per_page=20, error_out=False
   )
   
   return render_template('admin/manage_users.html', 
                        users=users, 
                        search=search, 
                        role_filter=role_filter)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
   """Créer un nouvel utilisateur"""
   form = UserCreationForm()
   if form.validate_on_submit():
       username = form.username.data
       email = form.email.data
       password = form.password.data
       role = form.role.data
       is_active = form.is_active.data
       
       try:
           user = User(
               username=username,
               email=email,
               role=role,
               is_active=is_active
           )
           user.set_password(password)
           
           db.session.add(user)
           db.session.commit()
           
           flash(f'Utilisateur {username} créé avec succès!', 'success')
           return redirect(url_for('admin.manage_users'))
           
       except Exception as e:
           db.session.rollback()
           flash(f'Erreur lors de la création de l\'utilisateur: {e}', 'error')
   
   return render_template('admin/create_user.html', form=form)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(original_username=user.username, original_email=user.email, obj=user)
    
    # Empêcher un admin de changer son propre rôle ou de se désactiver
    if current_user.id == user.id and user.is_admin():
        # Si l'utilisateur est l'admin actuel, il ne peut pas changer son propre rôle ou se désactiver
        form.role.choices = [('admin', 'Administrateur')] # Force le rôle à admin
        form.is_active.render_kw = {'disabled': 'disabled'} # Désactive le champ is_active
        if request.method == 'POST':
            form.role.data = 'admin' # S'assurer que le rôle reste admin même si le JS est contourné
            form.is_active.data = True # S'assurer que l'utilisateur reste actif
    
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            user.role = form.role.data
            user.is_active = form.is_active.data
            db.session.commit()
            flash(f'Utilisateur {user.username} mis à jour avec succès!', 'success')
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la mise à jour de l\'utilisateur: {e}', 'error')
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
   """Activer/désactiver un utilisateur"""
   user = User.query.get_or_404(user_id)
   
   # Empêcher la désactivation de son propre compte
   if user.id == current_user.id:
       return jsonify({'success': False, 'message': 'Vous ne pouvez pas désactiver votre propre compte.'})
   
   try:
       user.is_active = not user.is_active
       db.session.commit()
       
       status = 'activé' if user.is_active else 'désactivé'
       return jsonify({
           'success': True, 
           'message': f'Utilisateur {status} avec succès.',
           'is_active': user.is_active
       })
       
   except Exception as e:
       db.session.rollback()
       return jsonify({'success': False, 'message': 'Erreur lors de la modification du statut.'})

@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@admin_required
def change_user_role(user_id):
   """Changer le rôle d'un utilisateur"""
   user = User.query.get_or_404(user_id)
   new_role = request.json.get('role')
   
   if new_role not in ['admin', 'creator', 'user']:
       return jsonify({'success': False, 'message': 'Rôle invalide.'})
   
   # Empêcher la modification de son propre rôle
   if user.id == current_user.id:
       return jsonify({'success': False, 'message': 'Vous ne pouvez pas modifier votre propre rôle.'})
   
   try:
       user.role = new_role
       db.session.commit()
       
       return jsonify({
           'success': True, 
           'message': f'Rôle modifié en {user.get_role_display()}.',
           'role': new_role,
           'role_display': user.get_role_display(),
           'role_badge_class': user.get_role_badge_class()
       })
       
   except Exception as e:
       db.session.rollback()
       return jsonify({'success': False, 'message': 'Erreur lors de la modification du rôle.'})

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.id == user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte administrateur!', 'danger')
    else:
        try:
            db.session.delete(user)
            db.session.commit()
            flash(f'Utilisateur {user.username} supprimé avec succès!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la suppression de l\'utilisateur: {e}', 'danger')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/forms_management') # Renommé pour éviter le conflit avec /forms
@admin_required
def manage_forms():
   """Gestion des formulaires"""
   page = request.args.get('page', 1, type=int)
   search = request.args.get('search', '', type=str)
   
   query = Form.query.join(User)
   
   if search:
       query = query.filter(
           (Form.title.contains(search)) |
           (User.username.contains(search))
       )
   
   forms = query.order_by(Form.created_at.desc()).paginate(
       page=page, per_page=20, error_out=False
   )
   
   return render_template('admin/manage_forms.html', forms=forms, search=search)

@admin_bp.route('/forms/<int:form_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_form_status(form_id):
   """Activer/désactiver un formulaire"""
   form = Form.query.get_or_404(form_id)
   
   try:
       form.is_active = not form.is_active
       db.session.commit()
       
       status = 'activé' if form.is_active else 'désactivé'
       return jsonify({
           'success': True, 
           'message': f'Formulaire {status} avec succès.',
           'is_active': form.is_active
       })
       
   except Exception as e:
       db.session.rollback()
       return jsonify({'success': False, 'message': 'Erreur lors de la modification du statut.'})

@admin_bp.route('/forms/<int:form_id>/delete', methods=['POST'])
@admin_required
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    try:
        db.session.delete(form)
        db.session.commit()
        flash(f'Formulaire "{form.title}" supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du formulaire: {e}', 'danger')
    return redirect(url_for('admin.manage_forms'))

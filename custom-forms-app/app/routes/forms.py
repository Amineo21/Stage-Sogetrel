from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Form, FormResponse, FormShare, User
from app.forms import FormBuilderForm, ShareForm
from datetime import datetime
import json
import os
from app.utils.helpers import save_file, delete_file, get_file_size, get_file_extension, generate_unique_filename
from app.utils.exports import export_to_excel
from app.utils.email_service import send_form_submission_email
import uuid
import base64 # Ajout de l'importation de base64

forms_bp = Blueprint('forms', __name__)

# Helper pour vérifier les permissions de créateur
def creator_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_creator():
            flash('Accès non autorisé. Vous devez être un créateur de formulaires.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Helper pour vérifier l'accès au formulaire (propriétaire ou partagé)
def form_access_required(f):
    @login_required
    def decorated_function(form_id, *args, **kwargs):
        form = Form.query.get_or_404(form_id)
        if form.user_id != current_user.id:
            # Vérifier si le formulaire est partagé avec l'utilisateur actuel
            share = FormShare.query.filter_by(form_id=form.id, shared_with_id=current_user.id).first()
            if not share:
                flash('Accès non autorisé à ce formulaire.', 'danger')
                return redirect(url_for('forms.list_forms'))
            # Si partagé, s'assurer que l'utilisateur a la permission de voir les réponses
            if not share.can_view_responses:
                flash('Vous n\'avez pas la permission de voir les réponses de ce formulaire.', 'danger')
                return redirect(url_for('forms.list_forms'))
        return f(form_id, *args, **kwargs)
    return decorated_function

@forms_bp.route('/list')
@login_required
def list_forms():
    # Formulaires créés par l'utilisateur actuel
    my_forms = Form.query.filter_by(user_id=current_user.id).order_by(Form.created_at.desc()).all()
    
    # Formulaires partagés avec l'utilisateur actuel
    shared_forms_entries = FormShare.query.filter_by(shared_with_id=current_user.id).all()
    shared_forms_ids = [s.form_id for s in shared_forms_entries]
    shared_forms = Form.query.filter(Form.id.in_(shared_forms_ids)).order_by(Form.created_at.desc()).all()

    return render_template('forms/list.html', my_forms=my_forms, shared_forms=shared_forms)

@forms_bp.route('/create', methods=['GET', 'POST'])
@creator_required
def create_form():
    form = FormBuilderForm()
    if form.validate_on_submit():
        # Le form_data sera envoyé via JS après la construction du formulaire
        # Pour l'instant, nous créons un formulaire vide ou avec des données par défaut
        new_form = Form(
            title=form.title.data,
            description=form.description.data,
            user_id=current_user.id,
            form_data=json.dumps([]), # Initialiser avec un tableau JSON vide
            is_active=form.is_active.data,
            allow_anonymous=form.allow_anonymous.data,
            require_login_to_view=form.require_login_to_view.data,
            send_email_on_submit=form.send_email_on_submit.data,
            email_recipients=form.email_recipients.data
        )
        db.session.add(new_form)
        db.session.commit()
        flash('Formulaire créé avec succès! Vous pouvez maintenant ajouter des champs.', 'success')
        return redirect(url_for('forms.edit_form', form_id=new_form.id))
    return render_template('forms/create.html', form=form)

@forms_bp.route('/edit/<int:form_id>', methods=['GET', 'POST'])
@creator_required
def edit_form(form_id):
    form_obj = Form.query.get_or_404(form_id)
    if form_obj.user_id != current_user.id:
        # Vérifier si l'utilisateur a la permission d'édition via FormShare
        share = FormShare.query.filter_by(form_id=form_obj.id, shared_with_id=current_user.id).first()
        if not share or not share.can_edit:
            flash('Accès non autorisé à l\'édition de ce formulaire.', 'danger')
            return redirect(url_for('forms.list_forms'))

    form = FormBuilderForm(obj=form_obj) # Pré-remplir le formulaire avec les données existantes

    if form.validate_on_submit():
        form_obj.title = form.title.data
        form_obj.description = form.description.data
        form_obj.is_active = form.is_active.data
        form_obj.allow_anonymous = form.allow_anonymous.data
        form_obj.require_login_to_view = form.require_login_to_view.data
        form_obj.send_email_on_submit = form.send_email_on_submit.data
        form_obj.email_recipients = form.email_recipients.data
        form_obj.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Paramètres du formulaire mis à jour avec succès!', 'success')
        return redirect(url_for('forms.edit_form', form_id=form_obj.id)) # Rester sur la page d'édition

    # Passer les données du formulaire existant au template pour le constructeur JS
    existing_form_data = json.dumps(form_obj.form_data) if form_obj.form_data else '[]'
    return render_template('forms/edit.html', form=form, form_obj=form_obj, existing_form_data=existing_form_data)

@forms_bp.route('/delete/<int:form_id>', methods=['POST'])
@creator_required
def delete_form(form_id):
    form_obj = Form.query.get_or_404(form_id)
    if form_obj.user_id != current_user.id:
        flash('Accès non autorisé à la suppression de ce formulaire.', 'danger')
        return redirect(url_for('forms.list_forms'))
    
    try:
        # Supprimer les réponses associées
        FormResponse.query.filter_by(form_id=form_obj.id).delete()
        # Supprimer les partages associés
        FormShare.query.filter_by(form_id=form_obj.id).delete()
        
        db.session.delete(form_obj)
        db.session.commit()
        flash('Formulaire supprimé avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du formulaire: {e}', 'danger')
    return redirect(url_for('forms.list_forms'))

@forms_bp.route('/view/<int:form_id>')
def view_form(form_id):
    form_obj = Form.query.get_or_404(form_id)
    
    if form_obj.require_login_to_view and not current_user.is_authenticated:
        flash('Vous devez être connecté pour voir ce formulaire.', 'info')
        return redirect(url_for('auth.login', next=request.url))

    # Vérifier si l'utilisateur a accès si le formulaire n'est pas public
    if not form_obj.allow_anonymous and form_obj.user_id != current_user.id:
        if not current_user.is_authenticated:
            flash('Ce formulaire n\'est pas accessible aux utilisateurs non connectés.', 'danger')
            return redirect(url_for('auth.login', next=request.url))
        
        share = FormShare.query.filter_by(form_id=form_obj.id, shared_with_id=current_user.id).first()
        if not share:
            flash('Accès non autorisé à ce formulaire.', 'danger')
            return redirect(url_for('main.dashboard')) # Ou une page d'erreur

    return render_template('forms/view.html', form_obj=form_obj)

@forms_bp.route('/fill/<int:form_id>', methods=['GET', 'POST'])
def fill_form(form_id):
    form_obj = Form.query.get_or_404(form_id)

    if form_obj.require_login_to_view and not current_user.is_authenticated:
        flash('Vous devez être connecté pour remplir ce formulaire.', 'info')
        return redirect(url_for('auth.login', next=request.url))

    if not form_obj.is_active:
        flash('Ce formulaire n\'est pas actif et ne peut pas être rempli.', 'danger')
        return redirect(url_for('main.dashboard'))

    if not form_obj.allow_anonymous and not current_user.is_authenticated:
        flash('Ce formulaire ne peut pas être rempli anonymement. Veuillez vous connecter.', 'info')
        return redirect(url_for('auth.login', next=request.url))

    if request.method == 'POST':
        response_data = {}
        additional_emails = []
        
        # Traiter les champs du formulaire
        for field in form_obj.form_data:
            field_id = field.get('id')
            field_type = field.get('type')
            field_name = field.get('name') # Utiliser le nom du champ pour les données POST

            if field_type == 'file':
                if field_name in request.files and request.files[field_name].filename != '':
                    file = request.files[field_name]
                    filename = save_file(file, current_app.config['UPLOAD_FOLDER']) # Correction ici: save_uploaded_file -> save_file
                    if filename:
                        response_data[field_id] = {
                            'filename': filename,
                            'original_name': file.filename,
                            'size': get_file_size(os.path.join(current_app.config['UPLOAD_FOLDER'], filename)),
                            'extension': get_file_extension(filename)
                        }
                    else:
                        flash(f'Erreur lors de l\'upload du fichier pour {field_name}.', 'danger')
                        return redirect(url_for('forms.fill_form', form_id=form_id))
                else:
                    response_data[field_id] = None # Pas de fichier uploadé
            elif field_type == 'signature':
                signature_data = request.form.get(field_name)
                if signature_data:
                    # Sauvegarder la signature comme une image PNG
                    # Le chemin sera uploads/signatures/unique_id.png
                    signature_filename = generate_unique_filename('signatures', 'png')
                    signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures', signature_filename)
                    
                    # Assurez-vous que le dossier signatures existe
                    os.makedirs(os.path.dirname(signature_path), exist_ok=True)

                    try:
                        # Décoder la base64 et sauvegarder
                        header, encoded = signature_data.split(',', 1)
                        data = base64.b64decode(encoded)
                        with open(signature_path, 'wb') as f:
                            f.write(data)
                        response_data[field_id] = {
                            'filename': os.path.join('signatures', signature_filename), # Chemin relatif pour le stockage
                            'size': os.path.getsize(signature_path),
                            'extension': 'png'
                        }
                    except Exception as e:
                        flash(f'Erreur lors de la sauvegarde de la signature: {e}', 'danger')
                        response_data[field_id] = None
                else:
                    response_data[field_id] = None
            elif field_type == 'checkbox':
                # Les cases à cocher non cochées ne sont pas envoyées dans request.form
                # On doit vérifier si le nom du champ est présent
                response_data[field_id] = request.form.get(field_name) == 'on'
            elif field_type == 'radio':
                response_data[field_id] = request.form.get(field_name)
            elif field_type == 'select':
                response_data[field_id] = request.form.get(field_name)
            elif field_type == 'geolocation':
                lat = request.form.get(f'{field_name}_lat')
                lon = request.form.get(f'{field_name}_lon')
                if lat and lon:
                    response_data[field_id] = f"{lat},{lon}"
                else:
                    response_data[field_id] = None
            elif field_type == 'email':
                email_value = request.form.get(field_name)
                response_data[field_id] = email_value
                if field.get('is_recipient_email'): # Si ce champ est désigné comme email de destinataire
                    additional_emails.append(email_value)
            else:
                response_data[field_id] = request.form.get(field_name)

        user_id = current_user.id if current_user.is_authenticated else None
        ip_address = request.remote_addr

        new_response = FormResponse(
            form_id=form_id,
            user_id=user_id,
            response_data=json.dumps(response_data),
            ip_address=ip_address,
            additional_emails=','.join(additional_emails) if additional_emails else None
        )
        
        db.session.add(new_response)
        db.session.commit()

        flash('Votre réponse a été soumise avec succès!', 'success')

        # Envoyer l'email si configuré
        if form_obj.send_email_on_submit:
            recipients = []
            if form_obj.email_recipients:
                recipients.extend([e.strip() for e in form_obj.email_recipients.split(',') if e.strip()])
            if additional_emails:
                recipients.extend(additional_emails)
            
            if recipients:
                try:
                    send_form_submission_email(form_obj, new_response, recipients)
                    flash('Un email de confirmation a été envoyé.', 'info')
                except Exception as e:
                    flash(f'Erreur lors de l\'envoi de l\'email de confirmation: {e}', 'warning')

        return redirect(url_for('forms.view_form', form_id=form_id)) # Ou une page de confirmation

    return render_template('forms/fill.html', form_obj=form_obj)

@forms_bp.route('/responses/<int:form_id>')
@form_access_required
def view_responses(form_id):
    form_obj = Form.query.get_or_404(form_id)
    responses = FormResponse.query.filter_by(form_id=form_id).order_by(FormResponse.submitted_at.desc()).all()
    
    # Préparer les en-têtes de colonne pour le tableau
    # Utiliser les labels des champs du form_data
    column_headers = []
    if form_obj.form_data:
        for field in form_obj.form_data:
            column_headers.append(field.get('label', field.get('name', field.get('id'))))
    
    return render_template('forms/responses.html', form_obj=form_obj, responses=responses, column_headers=column_headers)

@forms_bp.route('/responses/<int:form_id>/export')
@form_access_required
def export_responses(form_id):
    form_obj = Form.query.get_or_404(form_id)
    responses = FormResponse.query.filter_by(form_id=form_id).order_by(FormResponse.submitted_at.asc()).all()

    try:
        # Le chemin de sortie sera un fichier temporaire
        output_filename = f"responses_{form_obj.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
        
        export_to_excel(form_obj, responses, output_path)
        
        return send_file(output_path, as_attachment=True, download_name=output_filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        flash(f'Erreur lors de l\'exportation des réponses: {e}', 'danger')
        current_app.logger.error(f"Error exporting form {form_id}: {e}")
        return redirect(url_for('forms.view_responses', form_id=form_id))

@forms_bp.route('/share/<int:form_id>', methods=['GET', 'POST'])
@creator_required
def share_form(form_id):
    form_obj = Form.query.get_or_404(form_id)
    if form_obj.user_id != current_user.id:
        flash('Vous ne pouvez partager que vos propres formulaires.', 'danger')
        return redirect(url_for('forms.list_forms'))

    form = ShareForm()
    if form.validate_on_submit():
        user_to_share_with = User.query.filter_by(email=form.email.data).first()
        if not user_to_share_with:
            flash('Utilisateur non trouvé avec cet email.', 'danger')
        elif user_to_share_with.id == current_user.id:
            flash('Vous ne pouvez pas partager un formulaire avec vous-même.', 'warning')
        else:
            existing_share = FormShare.query.filter_by(
                form_id=form_obj.id, 
                shared_with_id=user_to_share_with.id
            ).first()

            if existing_share:
                existing_share.can_edit = form.can_edit.data
                existing_share.can_view_responses = form.can_view_responses.data
                flash(f'Partage mis à jour pour {user_to_share_with.username}.', 'info')
            else:
                new_share = FormShare(
                    form_id=form_obj.id,
                    sharer_id=current_user.id,
                    shared_with_id=user_to_share_with.id,
                    can_edit=form.can_edit.data,
                    can_view_responses=form.can_view_responses.data
                )
                db.session.add(new_share)
                flash(f'Formulaire partagé avec {user_to_share_with.username}!', 'success')
            db.session.commit()
        return redirect(url_for('forms.share_form', form_id=form_id))
    
    # Afficher les partages existants
    existing_shares = FormShare.query.filter_by(form_id=form_id).all()
    
    return render_template('forms/share.html', form_obj=form_obj, form=form, existing_shares=existing_shares)

@forms_bp.route('/share/<int:share_id>/delete', methods=['POST'])
@creator_required
def delete_share(share_id):
    share = FormShare.query.get_or_404(share_id)
    # S'assurer que l'utilisateur actuel est le propriétaire du formulaire partagé
    if share.form.user_id != current_user.id:
        flash('Accès non autorisé à la suppression de ce partage.', 'danger')
        return redirect(url_for('forms.list_forms'))
    
    try:
        db.session.delete(share)
        db.session.commit()
        flash('Partage supprimé avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression du partage: {e}', 'danger')
    return redirect(url_for('forms.share_form', form_id=share.form_id))

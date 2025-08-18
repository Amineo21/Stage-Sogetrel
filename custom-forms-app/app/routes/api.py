from flask import Blueprint, jsonify, request, current_app, send_from_directory
from flask_login import login_required, current_user
from app.models import Form, FormResponse, FormFile, User, EmailLog, FormShare
from app import db
from app.utils.helpers import allowed_file, save_file, delete_file, get_file_size
from app.utils.exports import export_to_excel, export_to_pdf
from app.utils.email_service import send_form_submission_email
import os
import json
from datetime import datetime

api_bp = Blueprint('api', __name__)

# Helper pour vérifier les permissions d'édition (propriétaire ou partagé avec édition)
def form_edit_access_required(f):
    @login_required
    def decorated_function(form_id, *args, **kwargs):
        form = Form.query.get_or_404(form_id)
        if form.user_id != current_user.id:
            share = FormShare.query.filter_by(form_id=form.id, shared_with_id=current_user.id).first()
            if not share or not share.can_edit:
                return jsonify({'error': 'Accès non autorisé à l\'édition de ce formulaire.'}), 403
        return f(form_id, *args, **kwargs)
    return decorated_function

@api_bp.route('/forms/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    
    # Vérifier si le formulaire est actif
    if not form.is_active:
        return jsonify({'success': False, 'message': 'Ce formulaire n\'est pas actif et ne peut pas être soumis.'}), 403

    # Récupérer les données du formulaire
    form_data = request.form.to_dict()
    
    # Gérer les fichiers uploadés
    uploaded_files_data = []
    for field_name, file_storage in request.files.items():
        if file_storage and allowed_file(file_storage.filename):
            try:
                filename = save_file(file_storage, current_app.config['UPLOAD_FOLDER'])
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file_size = get_file_size(file_path)
                mime_type = file_storage.mimetype
                
                uploaded_files_data.append({
                    'field_id': field_name,
                    'filename': filename,
                    'original_filename': file_storage.filename,
                    'file_size': file_size,
                    'mime_type': mime_type
                })
                # Remplacer la valeur du champ par le nom du fichier sauvegardé
                form_data[field_name] = filename 
            except Exception as e:
                current_app.logger.error(f"Erreur lors de l'upload du fichier {file_storage.filename}: {e}")
                return jsonify({'success': False, 'message': f'Erreur lors de l\'upload du fichier {file_storage.filename}.'}), 500
        elif file_storage: # Fichier non autorisé ou vide
            current_app.logger.warning(f"Fichier non autorisé ou vide: {file_storage.filename}")
            return jsonify({'success': False, 'message': f'Type de fichier non autorisé ou fichier vide: {file_storage.filename}.'}), 400

    # Gérer la signature
    signature_data_url = form_data.pop('signature_data', None)
    signature_filename = None
    if signature_data_url:
        try:
            # La signature est une image base64, la sauvegarder comme fichier
            signature_filename = save_file(signature_data_url, current_app.config['UPLOAD_FOLDER'], is_base64=True)
            form_data['signature'] = signature_filename # Ajouter le nom du fichier de signature aux réponses
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la sauvegarde de la signature: {e}")
            return jsonify({'success': False, 'message': 'Erreur lors de la sauvegarde de la signature.'}), 500

    # Gérer la géolocalisation
    latitude = form_data.pop('latitude', None)
    longitude = form_data.pop('longitude', None)
    address = form_data.pop('address', None)

    # Gérer les emails additionnels
    additional_emails_str = form_data.pop('additional_emails', '')
    additional_emails = [e.strip() for e in additional_emails_str.split(',') if e.strip()]

    # Créer une nouvelle réponse
    response = FormResponse(
        form_id=form.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        responses_json=json.dumps(form_data),
        ip_address=request.remote_addr,
        latitude=latitude,
        longitude=longitude,
        address=address,
        signature_filename=signature_filename,
        additional_emails=json.dumps(additional_emails) if additional_emails else None
    )
    
    try:
        db.session.add(response)
        db.session.commit()

        # Enregistrer les fichiers liés à la réponse
        for file_data in uploaded_files_data:
            form_file = FormFile(
                form_id=form.id,
                response_id=response.id,
                field_id=file_data['field_id'],
                filename=file_data['filename'],
                original_filename=file_data['original_filename'],
                file_size=file_data['file_size'],
                mime_type=file_data['mime_type']
            )
            db.session.add(form_file)
        db.session.commit()

        # Envoi d'emails si activé
        if form.auto_email_enabled:
            recipient_list = []
            
            # Ajouter le créateur du formulaire
            if form.creator and form.creator.email:
                recipient_list.append(form.creator.email)
            
            # Ajouter les destinataires fixes
            recipient_list.extend(form.fixed_recipients_list)
            
            # Ajouter les emails additionnels saisis par l'utilisateur
            recipient_list.extend(additional_emails)
            
            # Supprimer les doublons et les emails vides
            recipient_list = list(set(filter(None, recipient_list)))

            if recipient_list:
                try:
                    send_form_submission_email(form, response, recipient_list)
                    current_app.logger.info(f"Emails envoyés pour la réponse {response.id} du formulaire {form.id}")
                except Exception as e:
                    current_app.logger.error(f"Erreur lors de l'envoi des emails pour la réponse {response.id}: {e}")
                    # Ne pas bloquer la soumission du formulaire si l'email échoue
        
        return jsonify({'success': True, 'message': 'Formulaire soumis avec succès!', 'response_id': response.id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erreur lors de la soumission du formulaire {form.id}: {e}")
        return jsonify({'success': False, 'message': f'Erreur lors de la soumission du formulaire: {e}'}), 500

@api_bp.route('/forms/<int:form_id>/export/excel', methods=['GET'])
@login_required
def export_form_responses_excel(form_id):
    form = Form.query.get_or_404(form_id)
    if not current_user.can_view_form(form):
        return jsonify({'success': False, 'message': 'Accès non autorisé.'}), 403
    
    try:
        excel_file = export_to_excel(form)
        return excel_file
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'export Excel du formulaire {form_id}: {e}")
        return jsonify({'success': False, 'message': f'Erreur lors de l\'export Excel: {e}'}), 500

@api_bp.route('/forms/<int:form_id>/responses/<int:response_id>/export/pdf', methods=['GET'])
@login_required
def export_form_response_pdf(form_id, response_id):
    form = Form.query.get_or_404(form_id)
    response = FormResponse.query.get_or_404(response_id)
    
    if not current_user.can_view_form(form) or response.form_id != form.id:
        return jsonify({'success': False, 'message': 'Accès non autorisé.'}), 403
    
    try:
        pdf_file = export_to_pdf(form, response)
        return pdf_file
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'export PDF de la réponse {response_id} du formulaire {form_id}: {e}")
        return jsonify({'success': False, 'message': f'Erreur lors de l\'export PDF: {e}'}), 500

@api_bp.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    # Sécurité: s'assurer que le fichier est dans le dossier d'upload
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@api_bp.route('/forms/<int:form_id>/save_fields', methods=['POST'])
@form_edit_access_required
def save_form_fields(form_id):
    form_obj = Form.query.get_or_404(form_id)
    
    try:
        data = request.get_json()
        if not data or 'form_data' not in data:
            return jsonify({'error': 'Données de formulaire manquantes.'}), 400
        
        form_obj.form_data = json.dumps(data['form_data'])
        db.session.commit()
        return jsonify({'message': 'Champs du formulaire sauvegardés avec succès!'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving form fields for form {form_id}: {e}")
        return jsonify({'error': f'Erreur lors de la sauvegarde des champs du formulaire: {e}'}), 500

@api_bp.route('/forms/<int:form_id>/get_fields', methods=['GET'])
@form_edit_access_required
def get_form_fields(form_id):
    form_obj = Form.query.get_or_404(form_id)
    
    try:
        if form_obj.form_data:
            return jsonify(json.loads(form_obj.form_data)), 200
        else:
            return jsonify([]), 200 # Retourne un tableau vide si pas de données
    except Exception as e:
        current_app.logger.error(f"Error getting form fields for form {form_id}: {e}")
        return jsonify({'error': f'Erreur lors de la récupération des champs du formulaire: {e}'}), 500

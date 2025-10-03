"""
Service d'envoi d'emails pour les formulaires
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app, render_template, url_for
from threading import Thread
from datetime import datetime
import json
import tempfile

from app import db
from app.models import EmailLog

def send_email_async(app, msg, email_log_entry):
    """Fonction asynchrone pour envoyer un email"""
    with app.app_context():
        try:
            # Configuration SMTP
            smtp_server = app.config.get('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(app.config.get('SMTP_PORT', 587))
            smtp_username = app.config.get('SMTP_USERNAME', '')
            smtp_password = app.config.get('SMTP_PASSWORD', '')
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            email_log_entry.status = 'sent'
            email_log_entry.error_message = None
        except Exception as e:
            email_log_entry.status = 'failed'
            email_log_entry.error_message = str(e)
            current_app.logger.error(f"Failed to send email: {e}")
        finally:
            db.session.add(email_log_entry)
            db.session.commit()


def send_email(recipient, subject, html_body, **kwargs):
    """
    Envoie un email simple
    
    Args:
        recipient: Adresse email du destinataire
        subject: Sujet de l'email
        html_body: Corps de l'email en HTML
        **kwargs: Arguments supplémentaires (user_id, form_id, etc.)
    """
    app = current_app._get_current_object()
    
    msg = MIMEMultipart('alternative')
    msg['From'] = app.config.get('MAIL_DEFAULT_SENDER', app.config.get('SMTP_USERNAME'))
    msg['To'] = recipient
    msg['Subject'] = subject
    
    # Attacher le corps HTML
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(html_part)
    
    # Créer une entrée de log avant l'envoi
    email_log_entry = EmailLog(
        recipient_email=recipient,
        subject=subject,
        body_preview=html_body[:500],
        status='pending',
        user_id=kwargs.get('user_id'),
        form_id=kwargs.get('form_id')
    )
    db.session.add(email_log_entry)
    db.session.commit()
    
    # Envoyer l'email de manière asynchrone
    Thread(target=send_email_async, args=(app, msg, email_log_entry)).start()


def send_form_submission_email(form_obj, form_response, recipients):
    """
    Envoie un email de notification pour une nouvelle soumission de formulaire
    
    Args:
        form_obj: Objet Form
        form_response: Objet FormResponse
        recipients: Liste des adresses email des destinataires
    """
    from app.utils.exports import export_to_excel, export_to_pdf
    
    subject = f"Nouvelle soumission pour le formulaire: {form_obj.title}"
    
    # Préparer les données de la réponse pour l'email
    response_details = []
    response_data = json.loads(form_response.response_data) if isinstance(form_response.response_data, str) else form_response.response_data
    
    for field in form_obj.form_data:
        field_id = field.get('id')
        field_label = field.get('label', field.get('name', field_id))
        field_type = field.get('type')
        value = response_data.get(field_id)

        if field_type == 'file' and value and isinstance(value, dict) and 'filename' in value:
            file_url = url_for('static', filename=os.path.join('uploads', value['filename']), _external=True)
            response_details.append(f"<li><strong>{field_label}:</strong> <a href='{file_url}'>{value.get('original_name', value['filename'])}</a> ({value.get('size', 'N/A')} bytes)</li>")
        elif field_type == 'signature' and value and isinstance(value, dict) and 'filename' in value:
            signature_url = url_for('static', filename=os.path.join('uploads', value['filename']), _external=True)
            response_details.append(f"<li><strong>{field_label}:</strong> <img src='{signature_url}' alt='Signature' style='max-width:200px;border:1px solid #ccc;'/></li>")
        elif field_type == 'geolocation' and value:
            response_details.append(f"<li><strong>{field_label}:</strong> <a href='https://www.google.com/maps/search/?api=1&query={value}' target='_blank'>{value}</a></li>")
        elif field_type == 'checkbox':
            response_details.append(f"<li><strong>{field_label}:</strong> {'Oui' if value else 'Non'}</li>")
        else:
            response_details.append(f"<li><strong>{field_label}:</strong> {value if value else 'Non renseigné'}</li>")

    # Générer le corps de l'email
    username = 'Anonyme'
    if hasattr(form_response, 'user') and form_response.user:
        username = form_response.user.username
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .info-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ padding: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Nouvelle réponse au formulaire</h1>
            <h2>{form_obj.title}</h2>
        </div>
        
        <div class="content">
            <div class="info-box">
                <h3>Informations de la soumission</h3>
                <p><strong>Soumis par :</strong> {username}</p>
                <p><strong>Date :</strong> {form_response.submitted_at.strftime('%d/%m/%Y à %H:%M')}</p>
                <p><strong>Adresse IP :</strong> {form_response.ip_address or 'Non disponible'}</p>
            </div>
            
            <h3>Réponses au formulaire</h3>
            <ul>
                {''.join(response_details)}
            </ul>
        </div>
        
        <div class="footer">
            <p>Cet email a été généré automatiquement par le système de formulaires.</p>
            <p>Date d'envoi : {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
        </div>
    </body>
    </html>
    """
    
    # Envoyer à chaque destinataire
    for recipient_email in recipients:
        try:
            app = current_app._get_current_object()
            
            msg = MIMEMultipart('alternative')
            msg['From'] = app.config.get('MAIL_DEFAULT_SENDER', app.config.get('SMTP_USERNAME'))
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Attacher le corps HTML
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Générer et attacher le PDF
            try:
                pdf_buffer = export_to_pdf(form_obj, [form_response])
                pdf_part = MIMEBase('application', 'pdf')
                pdf_part.set_payload(pdf_buffer.read())
                encoders.encode_base64(pdf_part)
                pdf_part.add_header('Content-Disposition', f'attachment; filename="{form_obj.title}_response.pdf"')
                msg.attach(pdf_part)
            except Exception as e:
                current_app.logger.error(f"Erreur lors de la génération du PDF: {e}")
            
            # Générer et attacher l'Excel
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    export_to_excel(form_obj, [form_response], tmp_file.name)
                    tmp_file.seek(0)
                    
                    with open(tmp_file.name, 'rb') as f:
                        excel_part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        excel_part.set_payload(f.read())
                        encoders.encode_base64(excel_part)
                        excel_part.add_header('Content-Disposition', f'attachment; filename="{form_obj.title}_data.xlsx"')
                        msg.attach(excel_part)
                    
                    # Supprimer le fichier temporaire
                    os.unlink(tmp_file.name)
            except Exception as e:
                current_app.logger.error(f"Erreur lors de la génération de l'Excel: {e}")
            
            # Créer une entrée de log
            email_log_entry = EmailLog(
                recipient_email=recipient_email,
                subject=subject,
                body_preview=html_body[:500],
                status='pending',
                user_id=form_response.user_id,
                form_id=form_obj.id
            )
            db.session.add(email_log_entry)
            db.session.commit()
            
            # Envoyer l'email de manière asynchrone
            Thread(target=send_email_async, args=(app, msg, email_log_entry)).start()
            
        except Exception as e:
            current_app.logger.error(f"Erreur lors de l'envoi de l'email à {recipient_email}: {e}")

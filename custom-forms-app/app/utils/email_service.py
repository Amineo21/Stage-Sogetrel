"""
Service d'envoi d'emails pour les formulaires
"""
import smtplib
import os
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app, render_template, url_for
from threading import Thread
from datetime import datetime
import json

from app import db
from app.models import EmailLog
from app.utils.exports import export_to_pdf, export_to_excel
from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    mail.init_app(app)

def _send_async_email(app, msg, email_log_entry):
    with app.app_context():
        try:
            mail.send(msg)
            email_log_entry.status = 'sent'
            email_log_entry.error_message = None
        except Exception as e:
            email_log_entry.status = 'failed'
            email_log_entry.error_message = str(e)
            current_app.logger.error(f"Failed to send email: {e}")
        finally:
            db.session.add(email_log_entry)
            db.session.commit()

def send_email(recipient, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(
        subject,
        sender=app.config.get('MAIL_DEFAULT_SENDER'),
        recipients=[recipient]
    )
    msg.html = render_template(template, **kwargs)

    # Créer une entrée de log avant l'envoi
    email_log_entry = EmailLog(
        recipient_email=recipient,
        subject=subject,
        body_preview=msg.html[:500], # Prévisualisation du corps
        status='pending',
        user_id=kwargs.get('user_id'), # Passer l'ID utilisateur si disponible
        form_id=kwargs.get('form_id') # Passer l'ID du formulaire si disponible
    )
    db.session.add(email_log_entry)
    db.session.commit() # Commit pour obtenir l'ID de l'entrée de log

    Thread(target=_send_async_email, args=(app, msg, email_log_entry)).start()

class EmailService:
    """Service pour l'envoi d'emails avec pièces jointes"""
    
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', self.smtp_username)
        self.from_name = os.environ.get('FROM_NAME', 'Système de Formulaires')
    
    def send_form_response_email(self, form, response, recipient_email, email_type='creator'):
        """
        Envoyer un email avec les réponses du formulaire en pièce jointe
        
        Args:
            form: Objet Form
            response: Objet FormResponse
            recipient_email: Email du destinataire
            email_type: Type d'email ('creator', 'fixed_recipient', 'additional')
        
        Returns:
            bool: True si envoyé avec succès, False sinon
        """
        try:
            # Créer le log d'email
            email_log = EmailLog(
                response_id=response.id,
                recipient_email=recipient_email,
                email_type=email_type,
                status='pending'
            )
            db.session.add(email_log)
            db.session.flush()
            
            # Générer les fichiers PDF et Excel
            pdf_content = self._generate_pdf_content(form, response)
            excel_content = self._generate_excel_content(form, response)
            
            if not pdf_content or not excel_content:
                email_log.status = 'failed'
                email_log.error_message = 'Erreur lors de la génération des fichiers'
                db.session.commit()
                return False
            
            # Créer le message email
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = f"Nouvelle réponse au formulaire : {form.title}"
            
            # Corps du message
            body = self._create_email_body(form, response, email_type)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Ajouter les pièces jointes
            self._attach_file(msg, pdf_content, f"{form.title}_reponse.pdf", 'application/pdf')
            self._attach_file(msg, excel_content, f"{form.title}_donnees.xlsx", 
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            # Envoyer l'email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            # Marquer comme envoyé
            email_log.status = 'sent'
            db.session.commit()
            
            print(f"Email envoyé avec succès à {recipient_email}")
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email à {recipient_email}: {str(e)}")
            
            # Marquer comme échoué
            if 'email_log' in locals():
                email_log.status = 'failed'
                email_log.error_message = str(e)
                db.session.commit()
            
            return False
    
    def send_all_emails_for_response(self, form, response):
        """
        Envoyer tous les emails pour une réponse de formulaire
        
        Args:
            form: Objet Form
            response: Objet FormResponse
        
        Returns:
            dict: Statistiques d'envoi
        """
        stats = {
            'total': 0,
            'sent': 0,
            'failed': 0,
            'recipients': []
        }
        
        # Email au créateur du formulaire
        if form.creator and form.creator.email:
            stats['total'] += 1
            if self.send_form_response_email(form, response, form.creator.email, 'creator'):
                stats['sent'] += 1
                stats['recipients'].append(form.creator.email)
            else:
                stats['failed'] += 1
        
        # Emails aux destinataires fixes
        for recipient in form.recipients:
            if recipient and '@' in recipient:
                stats['total'] += 1
                if self.send_form_response_email(form, response, recipient, 'fixed_recipient'):
                    stats['sent'] += 1
                    stats['recipients'].append(recipient)
                else:
                    stats['failed'] += 1
        
        # Emails additionnels saisis lors du remplissage
        for email in response.extra_emails:
            if email and '@' in email:
                stats['total'] += 1
                if self.send_form_response_email(form, response, email, 'additional'):
                    stats['sent'] += 1
                    stats['recipients'].append(email)
                else:
                    stats['failed'] += 1
        
        # Marquer la réponse comme traitée
        response.email_sent = True
        db.session.commit()
        
        return stats
    
    def _generate_pdf_content(self, form, response):
        """Générer le contenu PDF"""
        try:
            pdf_response = export_to_pdf(form, [response])
            return pdf_response.get_data()
        except Exception as e:
            print(f"Erreur lors de la génération du PDF: {e}")
            return None
    
    def _generate_excel_content(self, form, response):
        """Générer le contenu Excel"""
        try:
            excel_response = export_to_excel(form, [response])
            return excel_response.get_data()
        except Exception as e:
            print(f"Erreur lors de la génération de l'Excel: {e}")
            return None
    
    def _create_email_body(self, form, response, email_type):
        """Créer le corps de l'email"""
        user_name = response.user.username if response.user else 'Utilisateur anonyme'
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Nouvelle réponse au formulaire</h1>
                <h2>{form.title}</h2>
            </div>
            
            <div class="content">
                <div class="info-box">
                    <h3>Informations de la soumission</h3>
                    <p><strong>Soumis par :</strong> {user_name}</p>
                    <p><strong>Date :</strong> {response.submitted_at.strftime('%d/%m/%Y à %H:%M')}</p>
                    <p><strong>Adresse IP :</strong> {response.ip_address or 'Non disponible'}</p>
        """
        
        # Ajouter les informations de géolocalisation si disponibles
        if response.latitude and response.longitude:
            body += f"""
                    <p><strong>Coordonnées GPS :</strong> {response.latitude:.6f}, {response.longitude:.6f}</p>
            """
        
        if response.address:
            body += f"""
                    <p><strong>Adresse :</strong> {response.address}</p>
            """
        
        body += """
                </div>
                
                <h3>Réponses au formulaire</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Champ</th>
                            <th>Réponse</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Ajouter les réponses
        for field in form.fields:
            field_name = field['name']
            field_label = field.get('label', field_name)
            field_value = response.responses.get(field_name, 'Non renseigné')
            field_type = field.get('type', 'text')
            
            # Traitement spécial pour certains types
            if field_type == 'checkbox':
                field_value = 'Oui' if field_value else 'Non'
            elif field_type in ['file', 'signature'] and field_value and field_value != 'Non renseigné':
                field_value = f"Fichier joint : {field_value}"
            
            body += f"""
                        <tr>
                            <td><strong>{field_label}</strong></td>
                            <td>{field_value}</td>
                        </tr>
            """
        
        body += """
                    </tbody>
                </table>
                
                <div class="info-box">
                    <h4>Pièces jointes</h4>
                    <p>📄 <strong>Formulaire complet (PDF) :</strong> Version visuelle avec toutes les réponses</p>
                    <p>📊 <strong>Données (Excel) :</strong> Réponses sous forme de tableau pour analyse</p>
                </div>
            </div>
            
            <div class="footer">
                <p>Cet email a été généré automatiquement par le système de formulaires.</p>
                <p>Date d'envoi : {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _attach_file(self, msg, content, filename, content_type):
        """Ajouter une pièce jointe au message"""
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}'
        )
        msg.attach(part)
    
    def test_email_configuration(self):
        """Tester la configuration email"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            return True, "Configuration email valide"
        except Exception as e:
            return False, f"Erreur de configuration email: {str(e)}"
    
    def send_form_submission_email(self, form_obj, form_response, recipients):
        subject = f"Nouvelle soumission pour le formulaire: {form_obj.title}"
        
        # Préparer les données de la réponse pour l'email
        response_details = []
        response_data = json.loads(form_response.response_data)
        
        for field in form_obj.form_data:
            field_id = field.get('id')
            field_label = field.get('label', field.get('name', field_id))
            field_type = field.get('type')
            value = response_data.get(field_id)

            if field_type == 'file' and value and 'filename' in value:
                file_url = url_for('static', filename=os.path.join('uploads', value['filename']), _external=True)
                response_details.append(f"<li><strong>{field_label}:</strong> <a href='{file_url}'>{value.get('original_name', value['filename'])}</a> ({value.get('size', 'N/A')} bytes)</li>")
            elif field_type == 'signature' and value and 'filename' in value:
                signature_url = url_for('static', filename=os.path.join('uploads', value['filename']), _external=True)
                response_details.append(f"<li><strong>{field_label}:</strong> <img src='{signature_url}' alt='Signature' style='max-width:200px;border:1px solid #ccc;'/></li>")
            elif field_type == 'geolocation' and value:
                response_details.append(f"<li><strong>{field_label}:</strong> <a href='https://www.google.com/maps/search/?api=1&query={value}' target='_blank'>{value}</a></li>")
            elif field_type == 'checkbox':
                response_details.append(f"<li><strong>{field_label}:</strong> {'Oui' if value else 'Non'}</li>")
            else:
                response_details.append(f"<li><strong>{field_label}:</strong> {value if value else 'Non renseigné'}</li>")

        for recipient_email in recipients:
            send_email(
                recipient_email,
                subject,
                'emails/form_submission_notification.html',
                form=form_obj,
                response=form_response,
                response_details=response_details,
                user_id=form_response.user_id,
                form_id=form_obj.id
            )

# Instance globale du service email
email_service = EmailService()

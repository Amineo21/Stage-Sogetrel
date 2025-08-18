import openpyxl
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import json
import os
from PIL import Image as PILImage
import io
import base64
from flask import current_app, url_for

def export_to_excel(form_obj, responses, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = form_obj.title[:31] # Max 31 chars for sheet title

    # Définir les en-têtes de colonne
    headers = ['ID Réponse', 'Soumis par', 'Date de soumission', 'Adresse IP', 'Géolocalisation']
    field_ids = [] # Pour mapper les IDs de champ aux colonnes

    if form_obj.form_data:
        for field in form_obj.form_data:
            headers.append(field.get('label', field.get('name', field.get('id'))))
            field_ids.append(field.get('id'))

    ws.append(headers)

    # Style des en-têtes
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    for col_idx, cell in enumerate(ws[1]):
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        ws.column_dimensions[get_column_letter(col_idx + 1)].width = 20 # Largeur par défaut

    # Remplir les données
    for row_idx, response in enumerate(responses, start=2):
        row_data = [
            response.id,
            response.responder.username if response.responder else 'Anonyme',
            response.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            response.ip_address,
            response.geolocation
        ]
        
        response_content = json.loads(response.response_data)
        
        for field_id in field_ids:
            field_value = response_content.get(field_id)
            
            # Trouver le type de champ pour un traitement spécifique
            field_type = None
            for field_def in form_obj.form_data:
                if field_def.get('id') == field_id:
                    field_type = field_def.get('type')
                    break

            if field_type == 'file' and field_value and 'filename' in field_value:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], field_value['filename'])
                if os.path.exists(file_path):
                    row_data.append(f"Fichier: {field_value.get('original_name', field_value['filename'])}")
                    # Optionnel: Insérer le fichier si c'est une image
                    if field_value.get('extension') in ['png', 'jpg', 'jpeg', 'gif']:
                        try:
                            img = PILImage.open(file_path)
                            # Redimensionner l'image pour qu'elle tienne dans la cellule
                            max_width = 150
                            max_height = 100
                            img.thumbnail((max_width, max_height), PILImage.LANCZOS)
                            
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format=field_value.get('extension').upper())
                            img_byte_arr.seek(0)
                            
                            excel_img = ExcelImage(img_byte_arr)
                            # Positionner l'image dans la cellule correspondante
                            col_letter = get_column_letter(len(headers) - len(field_ids) + field_ids.index(field_id) + 1)
                            ws.add_image(excel_img, f'{col_letter}{row_idx}')
                            ws.row_dimensions[row_idx].height = max_height * 0.75 # Ajuster la hauteur de la ligne
                            ws.column_dimensions[col_letter].width = max_width / 7 # Ajuster la largeur de la colonne
                        except Exception as e:
                            current_app.logger.error(f"Could not insert image {file_path} into Excel: {e}")
                            row_data[-1] += " (Erreur d'insertion d'image)"
                else:
                    row_data.append(f"Fichier manquant: {field_value.get('original_name', field_value['filename'])}")
            elif field_type == 'signature' and field_value and 'filename' in field_value:
                signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], field_value['filename'])
                if os.path.exists(signature_path):
                    row_data.append("Signature")
                    try:
                        img = PILImage.open(signature_path)
                        max_width = 150
                        max_height = 100
                        img.thumbnail((max_width, max_height), PILImage.LANCZOS)
                        
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        excel_img = ExcelImage(img_byte_arr)
                        col_letter = get_column_letter(len(headers) - len(field_ids) + field_ids.index(field_id) + 1)
                        ws.add_image(excel_img, f'{col_letter}{row_idx}')
                        ws.row_dimensions[row_idx].height = max_height * 0.75
                        ws.column_dimensions[col_letter].width = max_width / 7
                    except Exception as e:
                        current_app.logger.error(f"Could not insert signature {signature_path} into Excel: {e}")
                        row_data[-1] += " (Erreur d'insertion de signature)"
                else:
                    row_data.append("Signature manquante")
            elif field_type == 'checkbox':
                row_data.append('Oui' if field_value else 'Non')
            elif field_type == 'geolocation':
                if field_value:
                    row_data.append(f"Lat,Lon: {field_value}")
                else:
                    row_data.append("Non renseigné")
            else:
                row_data.append(str(field_value) if field_value is not None else '')
        
        ws.append(row_data)

    # Ajuster la largeur des colonnes automatiquement
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        if adjusted_width > 50: # Limiter la largeur maximale pour éviter des colonnes trop larges
            adjusted_width = 50
        ws.column_dimensions[column].width = adjusted_width

    wb.save(output_path)

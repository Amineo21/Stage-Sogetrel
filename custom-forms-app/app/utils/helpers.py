"""
Fonctions utilitaires pour l'application
"""
import os
import uuid
import re
import mimetypes
import tempfile
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app
import base64
import imghdr # Pour vérifier le type d'image

# Extensions de fichiers autorisées
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz',
    'mp3', 'wav', 'flac', 'aac',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv'
}

# Extensions d'images
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'}

def allowed_file(filename):
    """
    Vérifier si le fichier a une extension autorisée
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        bool: True si l'extension est autorisée
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def is_image_file(filename):
    """
    Vérifier si le fichier est une image
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        bool: True si c'est une image
    """
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS

def get_file_extension(filename):
    """
    Obtenir l'extension d'un fichier
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        str: Extension du fichier (sans le point)
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def get_file_icon(filename):
    """
    Obtenir l'icône appropriée pour un type de fichier
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        str: Classe CSS de l'icône
    """
    if not filename:
        return 'fas fa-file'
    
    extension = get_file_extension(filename)
    
    icon_map = {
        # Images
        'png': 'fas fa-file-image',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'gif': 'fas fa-file-image',
        'webp': 'fas fa-file-image',
        'bmp': 'fas fa-file-image',
        'tiff': 'fas fa-file-image',
        
        # Documents
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'xls': 'fas fa-file-excel',
        'xlsx': 'fas fa-file-excel',
        'ppt': 'fas fa-file-powerpoint',
        'pptx': 'fas fa-file-powerpoint',
        'txt': 'fas fa-file-alt',
        
        # Archives
        'zip': 'fas fa-file-archive',
        'rar': 'fas fa-file-archive',
        '7z': 'fas fa-file-archive',
        'tar': 'fas fa-file-archive',
        'gz': 'fas fa-file-archive',
        
        # Audio
        'mp3': 'fas fa-file-audio',
        'wav': 'fas fa-file-audio',
        'flac': 'fas fa-file-audio',
        'aac': 'fas fa-file-audio',
        
        # Vidéo
        'mp4': 'fas fa-file-video',
        'avi': 'fas fa-file-video',
        'mov': 'fas fa-file-video',
        'wmv': 'fas fa-file-video',
        'flv': 'fas fa-file-video',
        'mkv': 'fas fa-file-video',
    }
    
    return icon_map.get(extension, 'fas fa-file')

def generate_unique_filename(subfolder=None, extension=None):
    """
    Génère un nom de fichier unique avec un UUID.
    """
    unique_id = str(uuid.uuid4())
    if extension:
        filename = f"{unique_id}.{extension}"
    else:
        filename = unique_id
    
    if subfolder:
        return os.path.join(subfolder, filename)
    return filename

def save_file(file_storage_or_base64_data, upload_folder, is_base64=False):
    """
    Sauvegarder un fichier uploadé ou une chaîne base64 dans le dossier d'upload.
    Retourne le nom de fichier généré.
    """
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    if is_base64:
        # Extraire le type MIME et les données base64
        match = re.match(r"data:(image/[^;]+);base64,(.*)", file_storage_or_base64_data)
        if not match:
            raise ValueError("Format de données base64 invalide.")
        
        mime_type = match.group(1)
        base64_data = match.group(2)
        
        # Déterminer l'extension à partir du type MIME
        if 'png' in mime_type:
            ext = 'png'
        elif 'jpeg' in mime_type:
            ext = 'jpeg'
        elif 'gif' in mime_type:
            ext = 'gif'
        else:
            raise ValueError(f"Type MIME non supporté pour base64: {mime_type}")
            
        filename = generate_unique_filename(subfolder='files', extension=ext)
        file_path = os.path.join(upload_folder, filename)
        
        try:
            img_data = base64.b64decode(base64_data)
            with open(file_path, 'wb') as f:
                f.write(img_data)
            
            # Vérifier si le fichier est bien une image après décodage
            if imghdr.what(file_path) is None:
                os.remove(file_path) # Supprimer le fichier si ce n'est pas une image valide
                raise ValueError("Les données base64 ne correspondent pas à une image valide.")
                
            return filename
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la sauvegarde du fichier base64: {e}")
            raise
    else:
        # Pour les objets FileStorage (uploads de formulaire)
        original_filename = secure_filename(file_storage_or_base64_data.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        filename = generate_unique_filename(subfolder='files', extension=extension)
        file_path = os.path.join(upload_folder, filename)
        
        try:
            file_storage_or_base64_data.save(file_path)
            return filename
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la sauvegarde du fichier uploadé: {e}")
            raise

def delete_file(filepath):
    """Supprime un fichier du système de fichiers."""
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting file {filepath}: {e}")
            return False
    return False

def get_file_size(filepath):
    """Retourne la taille d'un fichier en octets."""
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0

def get_geolocation_data(ip_address):
    """
    Simule la récupération des données de géolocalisation à partir d'une adresse IP.
    Dans une application réelle, vous utiliseriez un service tiers (ex: ipinfo.io, ip-api.com).
    """
    # Ceci est un placeholder. Dans une vraie application, vous feriez une requête API.
    # Exemple:
    # import requests
    # try:
    #     response = requests.get(f"http://ip-api.com/json/{ip_address}")
    #     data = response.json()
    #     if data['status'] == 'success':
    #         return {
    #             'latitude': data['lat'],
    #             'longitude': data['lon'],
    #             'address': f"{data['city']}, {data['regionName']}, {data['country']}"
    #         }
    # except Exception as e:
    #     current_app.logger.error(f"Erreur de géolocalisation pour {ip_address}: {e}")
    return {
        'latitude': None,
        'longitude': None,
        'address': 'Géolocalisation non disponible (simulée)'
    }

def format_file_size(size_bytes):
    """
    Formater la taille d'un fichier en format lisible
    
    Args:
        size_bytes (int): Taille en bytes
        
    Returns:
        str: Taille formatée (ex: "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_field_value(field_type, value, field_config=None):
    """
    Valider la valeur d'un champ selon son type
    
    Args:
        field_type (str): Type du champ
        value: Valeur à valider
        field_config (dict): Configuration du champ
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if field_config is None:
        field_config = {}
    
    # Champs obligatoires
    if field_config.get('required', False) and not value:
        return False, "Ce champ est obligatoire"
    
    # Si la valeur est vide et le champ n'est pas obligatoire
    if not value:
        return True, None
    
    # Validation par type
    if field_type == 'email':
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            return False, "Format d'email invalide"
    
    elif field_type == 'number':
        try:
            num_value = float(value)
            min_val = field_config.get('min')
            max_val = field_config.get('max')
            
            if min_val is not None and num_value < min_val:
                return False, f"La valeur doit être supérieure ou égale à {min_val}"
            
            if max_val is not None and num_value > max_val:
                return False, f"La valeur doit être inférieure ou égale à {max_val}"
                
        except ValueError:
            return False, "Doit être un nombre valide"
    
    elif field_type == 'tel':
        # Validation basique pour les numéros de téléphone
        phone_pattern = r'^[\d\s\-\+$$$$\.]{8,}$'
        if not re.match(phone_pattern, value):
            return False, "Format de téléphone invalide"
    
    elif field_type == 'url':
        url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        if not re.match(url_pattern, value):
            return False, "Format d'URL invalide"
    
    elif field_type == 'date':
        try:
            from datetime import datetime
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return False, "Format de date invalide (YYYY-MM-DD)"
    
    elif field_type == 'time':
        try:
            from datetime import datetime
            datetime.strptime(value, '%H:%M')
        except ValueError:
            return False, "Format d'heure invalide (HH:MM)"
    
    # Validation de longueur
    min_length = field_config.get('min_length')
    max_length = field_config.get('max_length')
    
    if min_length and len(str(value)) < min_length:
        return False, f"Minimum {min_length} caractères requis"
    
    if max_length and len(str(value)) > max_length:
        return False, f"Maximum {max_length} caractères autorisés"
    
    return True, None

def clean_filename(filename):
    """
    Nettoyer un nom de fichier pour éviter les caractères problématiques
    
    Args:
        filename (str): Nom de fichier original
        
    Returns:
        str: Nom de fichier nettoyé
    """
    if not filename:
        return "fichier"
    
    # Utiliser secure_filename de Werkzeug
    clean_name = secure_filename(filename)
    
    # Si le nom devient vide après nettoyage
    if not clean_name:
        extension = get_file_extension(filename)
        clean_name = f"fichier.{extension}" if extension else "fichier"
    
    return clean_name

def safe_delete_file(file_path):
    """
    Supprimer un fichier de manière sécurisée
    
    Args:
        file_path (str): Chemin vers le fichier à supprimer
        
    Returns:
        bool: True si la suppression a réussi
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            
            # Supprimer aussi la miniature si elle existe
            name, ext = os.path.splitext(file_path)
            thumbnail_path = f"{name}_thumb{ext}"
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            
            return True
    except Exception as e:
        print(f"Erreur lors de la suppression du fichier {file_path}: {e}")
    
    return False

def get_mime_type(filename):
    """
    Obtenir le type MIME d'un fichier
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        str: Type MIME
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def convert_image_to_base64(image_path):
    """
    Convertir une image en base64
    
    Args:
        image_path (str): Chemin vers l'image
        
    Returns:
        str: Image en base64 ou None
    """
    try:
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            mime_type = get_mime_type(image_path)
            return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"Erreur lors de la conversion en base64: {e}")
        return None

def is_safe_path(path, base_path):
    """
    Vérifier qu'un chemin est sécurisé (pas de directory traversal)
    
    Args:
        path (str): Chemin à vérifier
        base_path (str): Chemin de base autorisé
        
    Returns:
        bool: True si le chemin est sécurisé
    """
    try:
        # Résoudre les chemins absolus
        abs_base = os.path.abspath(base_path)
        abs_path = os.path.abspath(os.path.join(base_path, path))
        
        # Vérifier que le chemin reste dans le dossier de base
        return abs_path.startswith(abs_base)
    except Exception:
        return False

def optimize_image(image_path, max_size=(800, 600), quality=85):
    """
    Optimiser une image (redimensionner et compresser)
    
    Args:
        image_path (str): Chemin vers l'image
        max_size (tuple): Taille maximale (largeur, hauteur)
        quality (int): Qualité de compression (1-100)
        
    Returns:
        bool: True si l'optimisation a réussi
    """
    try:
        with Image.open(image_path) as img:
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionner si nécessaire
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Sauvegarder avec compression
            img.save(image_path, 'JPEG', optimize=True, quality=quality)
            
        return True
    except Exception as e:
        print(f"Erreur lors de l'optimisation de l'image: {e}")
        return False

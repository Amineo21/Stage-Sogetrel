#!/usr/bin/env python3
"""
Script de migration pour ajouter le champ address à la table form_responses
"""

import os
import sys
from app import create_app, db
from app.models import FormResponse
from sqlalchemy import Column, String
import pymysql
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin pour que 'app' soit importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_migration():
    """Exécuter la migration pour ajouter le champ address"""
    
    # Configuration de la base de données
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'custom_forms'),
        'charset': 'utf8mb4'
    }
    
    try:
        # Connexion à la base de données
        print("Connexion à la base de données...")
        connection = pymysql.connect(**config)
        
        with connection.cursor() as cursor:
            # Vérifier si la colonne existe déjà
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'form_responses' 
                AND COLUMN_NAME = 'address'
            """, (config['database'],))
            
            column_exists = cursor.fetchone()[0] > 0
            
            if column_exists:
                print("La colonne 'address' existe déjà dans la table 'form_responses'.")
                return True
            
            # Ajouter la colonne address
            print("Ajout de la colonne 'address' à la table 'form_responses'...")
            cursor.execute("""
                ALTER TABLE form_responses 
                ADD COLUMN address TEXT AFTER longitude
            """)
            
            # Valider les changements
            connection.commit()
            print("Migration réussie ! La colonne 'address' a été ajoutée.")
            
            # Vérifier que la colonne a été ajoutée
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'form_responses' 
                AND COLUMN_NAME = 'address'
            """, (config['database'],))
            
            if cursor.fetchone()[0] > 0:
                print("Vérification réussie : la colonne 'address' est présente.")
                return True
            else:
                print("Erreur : la colonne 'address' n'a pas été créée.")
                return False
                
    except pymysql.Error as e:
        print(f"Erreur MySQL : {e}")
        return False
    except Exception as e:
        print(f"Erreur : {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()
            print("Connexion fermée.")

def add_address_field_to_responses():
    app = create_app('development')
    with app.app_context():
        print("--- Ajout du champ 'address' à la table FormResponse ---")
        
        # Vérifier si le champ existe déjà pour éviter les erreurs
        inspector = db.inspect(db.engine)
        if 'form_response' in inspector.get_table_names() and 'address' in [c['name'] for c in inspector.get_columns('form_response')]:
            print("Le champ 'address' existe déjà dans la table 'form_response'. Aucune action nécessaire.")
            return

        # Ajouter la colonne 'address' au modèle FormResponse
        # Note: Ceci est une approche simplifiée pour un script.
        # Pour une gestion de migration robuste, utilisez Flask-Migrate.
        try:
            with db.engine.connect() as connection:
                connection.execute(db.text("ALTER TABLE form_response ADD COLUMN address VARCHAR(255)"))
                connection.commit()
            print("Champ 'address' ajouté à la table 'form_response' avec succès.")
            
            # Mettre à jour le modèle en mémoire pour cette session
            FormResponse.address = Column(String(255))
            
            # Optionnel: Mettre à jour les enregistrements existants avec une valeur par défaut
            # print("Mise à jour des enregistrements existants...")
            # for response in FormResponse.query.all():
            #     if response.address is None:
            #         response.address = "" # Ou une autre valeur par défaut
            # db.session.commit()
            # print("Enregistrements existants mis à jour.")

        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'ajout du champ 'address': {e}")

if __name__ == "__main__":
    print("=== Migration : Ajout du champ address ===")
    
    if run_migration():
        print("Migration terminée avec succès !")
    else:
        print("Échec de la migration.")
    
    add_address_field_to_responses()
    print("\nN'oubliez pas d'exécuter 'flask db migrate' et 'flask db upgrade' pour une gestion de migration propre.")

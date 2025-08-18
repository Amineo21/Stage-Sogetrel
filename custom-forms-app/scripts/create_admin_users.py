import sys
import os
from getpass import getpass
from app import create_app, db
from app.models import User

# Ajouter le répertoire parent au chemin pour que 'app' soit importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_admin_user():
    app = create_app('development') # Utiliser la configuration de développement
    with app.app_context():
        print("--- Création d'un utilisateur administrateur ---")
        
        username = input("Nom d'utilisateur: ")
        email = input("Email: ")
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            print(f"Un utilisateur avec ce nom d'utilisateur ou cet email existe déjà: {existing_user.username} ({existing_user.email}).")
            if input("Voulez-vous mettre à jour cet utilisateur en administrateur? (oui/non): ").lower() == 'oui':
                user = existing_user
                user.role = 'admin'
                user.is_active = True
                print(f"L'utilisateur {user.username} a été mis à jour en administrateur.")
            else:
                print("Opération annulée.")
                return
        else:
            password = getpass("Mot de passe: ")
            password2 = getpass("Confirmer le mot de passe: ")

            if password != password2:
                print("Les mots de passe ne correspondent pas.")
                return

            user = User(username=username, email=email, role='admin', is_active=True)
            user.set_password(password)
            db.session.add(user)
            print(f"L'utilisateur {username} a été créé avec le rôle administrateur.")

        try:
            db.session.commit()
            print("Opération terminée avec succès.")
        except Exception as e:
            db.session.rollback()
            print(f"Une erreur est survenue lors de la création/mise à jour de l'utilisateur: {e}")

if __name__ == '__main__':
    create_admin_user()

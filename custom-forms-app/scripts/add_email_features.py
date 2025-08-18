"""
Script de migration pour ajouter les fonctionnalités d'email
"""
import sys
import os
from app import create_app, db
from app.models import User, Form, FormResponse, EmailLog
from sqlalchemy import text, inspect

def run_migration():
    """Exécuter la migration pour ajouter les fonctionnalités d'email"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Début de la migration pour les fonctionnalités d'email...")
        
        # Ajouter la colonne role à la table users si elle n'existe pas
        print("📝 Ajout de la colonne 'role' à la table users...")
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
            print("✅ Colonne 'role' ajoutée avec succès")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("ℹ️  Colonne 'role' existe déjà")
            else:
                print(f"❌ Erreur lors de l'ajout de la colonne 'role': {e}")
        
        # Ajouter les colonnes email à la table forms
        print("📝 Ajout des colonnes d'email à la table forms...")
        inspector = db.inspect(db.engine)
        form_columns = [c['name'] for c in inspector.get_columns('forms')]
        
        if 'send_email_on_submit' in form_columns and 'email_recipients' in form_columns:
            print("Les champs 'send_email_on_submit' et 'email_recipients' existent déjà. Aucune action nécessaire.")
        else:
            try:
                with db.engine.connect() as connection:
                    if 'send_email_on_submit' not in form_columns:
                        connection.execute(db.text("ALTER TABLE forms ADD COLUMN send_email_on_submit BOOLEAN DEFAULT FALSE"))
                        print("Champ 'send_email_on_submit' ajouté.")
                    
                    if 'email_recipients' not in form_columns:
                        connection.execute(db.text("ALTER TABLE forms ADD COLUMN email_recipients VARCHAR(500)"))
                        print("Champ 'email_recipients' ajouté.")
                    
                    connection.commit()
                
                print("Champs d'email ajoutés à la table 'forms' avec succès.")
                
                # Mettre à jour les modèles en mémoire pour cette session
                Form.send_email_on_submit = db.Column(db.Boolean, default=False)
                Form.email_recipients = db.Column(db.String(500))
            except Exception as e:
                db.session.rollback()
                print(f"Erreur lors de l'ajout des champs d'email: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE forms ADD COLUMN email_recipients TEXT"))
            print("✅ Colonne 'email_recipients' ajoutée")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("ℹ️  Colonne 'email_recipients' existe déjà")
            else:
                print(f"❌ Erreur: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE forms ADD COLUMN auto_send_email BOOLEAN DEFAULT FALSE"))
            print("✅ Colonne 'auto_send_email' ajoutée")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("ℹ️  Colonne 'auto_send_email' existe déjà")
            else:
                print(f"❌ Erreur: {e}")
        
        # Ajouter les colonnes à la table form_responses
        print("📝 Ajout des colonnes à la table form_responses...")
        try:
            db.session.execute(text("ALTER TABLE form_responses ADD COLUMN additional_emails TEXT"))
            print("✅ Colonne 'additional_emails' ajoutée")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("ℹ️  Colonne 'additional_emails' existe déjà")
            else:
                print(f"❌ Erreur: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE form_responses ADD COLUMN email_sent BOOLEAN DEFAULT FALSE"))
            print("✅ Colonne 'email_sent' ajoutée")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("ℹ️  Colonne 'email_sent' existe déjà")
            else:
                print(f"❌ Erreur: {e}")
        
        # Créer la table email_logs
        print("📝 Création de la table email_logs...")
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_id INTEGER NOT NULL,
                    recipient_email VARCHAR(120) NOT NULL,
                    email_type VARCHAR(50) NOT NULL,
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    FOREIGN KEY (response_id) REFERENCES form_responses (id)
                )
            """))
            print("✅ Table 'email_logs' créée")
        except Exception as e:
            print(f"❌ Erreur lors de la création de la table email_logs: {e}")
        
        # Créer la table form_files si elle n'existe pas
        print("📝 Création de la table form_files...")
        try:
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS form_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_id INTEGER NOT NULL,
                    field_name VARCHAR(100) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size INTEGER,
                    mime_type VARCHAR(100),
                    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (response_id) REFERENCES form_responses (id)
                )
            """))
            print("✅ Table 'form_files' créée")
        except Exception as e:
            print(f"❌ Erreur lors de la création de la table form_files: {e}")
        
        # Mettre à jour les rôles des utilisateurs existants
        print("📝 Mise à jour des rôles utilisateurs...")
        try:
            # Définir le premier utilisateur comme admin
            first_user = User.query.first()
            if first_user and not first_user.role:
                first_user.role = 'admin'
                print(f"✅ Utilisateur '{first_user.username}' défini comme admin")
            
            # Définir les autres utilisateurs comme créateurs par défaut
            other_users = User.query.filter(User.id != (first_user.id if first_user else 0)).all()
            for user in other_users:
                if not user.role:
                    user.role = 'creator'
                    print(f"✅ Utilisateur '{user.username}' défini comme créateur")
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des rôles: {e}")
        
        # Valider toutes les modifications
        db.session.commit()
        print("✅ Migration terminée avec succès!")
        
        # Afficher un résumé
        print("\n📊 Résumé de la migration:")
        print(f"👥 Utilisateurs: {User.query.count()}")
        print(f"📋 Formulaires: {Form.query.count()}")
        print(f"📝 Réponses: {FormResponse.query.count()}")
        
        # Afficher les rôles
        print("\n👤 Rôles des utilisateurs:")
        for user in User.query.all():
            print(f"  - {user.username}: {user.role}")
        
    except Exception as e:
        print(f"❌ Erreur générale lors de la migration: {e}")
        db.session.rollback()
        return False
    
    return True

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n🎉 Migration terminée avec succès!")
        print("\n📋 Prochaines étapes:")
        print("1. Configurez les variables d'environnement SMTP dans votre .env")
        print("2. Redémarrez l'application: python run.py")
        print("3. Testez la création de formulaires avec envoi automatique")
        print("4. Exécutez 'flask db migrate' et 'flask db upgrade' pour une gestion de migration propre.")
    else:
        print("\n❌ La migration a échoué. Vérifiez les erreurs ci-dessus.")
        sys.exit(1)

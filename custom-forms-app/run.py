import os
from app import create_app, db
from flask_migrate import upgrade, migrate, init, stamp

# Définir l'environnement Flask
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

@app.cli.command('init-db')
def init_db_command():
    """Initialise la base de données."""
    with app.app_context():
        db.create_all()
    print('Base de données initialisée.')

@app.cli.command('migrate-db')
def migrate_db_command():
    """Exécute les migrations de base de données."""
    with app.app_context():
        # Vérifie si le répertoire de migrations existe, sinon l'initialise
        if not os.path.exists('migrations'):
            init()
        # Estampille la base de données avec la tête si elle n'est pas versionnée
        if not db.engine.dialect.has_table(db.engine, 'alembic_version'):
            stamp()
        migrate()
        upgrade()
    print('Base de données migrée.')

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask
from config import Config
from controllers.accueil import bp_accueil
from controllers.effectifs import bp_effectifs
from controllers.api import bp_api
from controllers.honoraires import bp_honoraires
from controllers.auth import bp_auth

# Base + moteur pour créer la table utilisateur si elle n'existe pas encore
from models.db import engine
from models.dimensions import Base
import models.utilisateur  # noqa: F401  (enregistre le modèle Utilisateur sur Base)

 
app = Flask(__name__)
app.config.from_object(Config)

# Enregistrement des blueprints
app.register_blueprint(bp_accueil)
app.register_blueprint(bp_effectifs)
app.register_blueprint(bp_api)
app.register_blueprint(bp_honoraires)
app.register_blueprint(bp_auth)

# Crée la table "utilisateur" si absente (ne touche pas aux tables existantes)
Base.metadata.create_all(engine)

if __name__ == "__main__":
    app.run(debug=True)
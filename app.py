from flask import Flask
from config import Config
from controllers.accueil import bp_accueil
from controllers.effectifs import bp_effectifs
from controllers.api import bp_api


app = Flask(__name__)
app.config.from_object(Config)

# Enregistrement des blueprints
app.register_blueprint(bp_accueil)
app.register_blueprint(bp_effectifs)
app.register_blueprint(bp_api)

if __name__ == "__main__":
    app.run(debug=True)
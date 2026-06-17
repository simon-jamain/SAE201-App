import os
from flask import Flask, render_template
from config import Config
from controllers.accueil import bp_accueil
from controllers.effectifs import bp_effectifs
from controllers.api import bp_api
from controllers.contact import bp_contact
from controllers.dashboard import bp_dashboard

app = Flask(__name__)
app.config.from_object(Config)

# Préfixe d'URL pour déploiement en sous-dossier (vide en local)
app.config["BASE_URL"] = os.getenv("APP_BASE_URL", "")


@app.context_processor
def inject_base_url():
    """Rend BASE_URL disponible dans tous les templates."""
    return {"BASE_URL": app.config["BASE_URL"]}


# ── Blueprints ────────────────────────────────────────────────────────────
app.register_blueprint(bp_accueil)
app.register_blueprint(bp_effectifs)
app.register_blueprint(bp_api)
app.register_blueprint(bp_contact)
app.register_blueprint(bp_dashboard) 


# ── Gestionnaires d'erreurs ───────────────────────────────────────────────
@app.errorhandler(404)
def page_non_trouvee(e):
    return render_template(
        "erreur.html",
        code=404,
        message="La page que vous cherchez n'existe pas ou a été déplacée."
    ), 404


@app.errorhandler(500)
def erreur_serveur(e):
    return render_template(
        "erreur.html",
        code=500,
        message="Une erreur interne est survenue. Réessayez dans quelques instants."
    ), 500


if __name__ == "__main__":
    app.run(debug=True)

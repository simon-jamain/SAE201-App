from flask import Blueprint, render_template

bp_accueil = Blueprint("accueil", __name__)


@bp_accueil.route("/")
@bp_accueil.route("/accueil")
def index():
    """Page d'accueil."""
    return render_template("accueil.html")
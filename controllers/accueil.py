from flask import Blueprint, render_template
from models.db import Session
from models.dimensions import Region, ProfessionSante

bp_accueil = Blueprint("accueil", __name__)


@bp_accueil.route("/")
@bp_accueil.route("/accueil")
def index():
    """Page d'accueil : formulaire de sélection."""
    session = Session()
    try:
        regions     = session.query(Region).order_by(Region.libelle).all()
        professions = session.query(ProfessionSante).order_by(ProfessionSante.libelle).all()
        return render_template("accueil.html", regions=regions, professions=professions)
    finally:
        session.close()

@bp_accueil.route("/presentation")
@bp_accueil.route("/presentation.html")
def presentation():
    return render_template("presentation.html")
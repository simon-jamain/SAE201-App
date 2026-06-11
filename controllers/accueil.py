from flask import Blueprint, render_template
from models.db import Session
from models.dimensions import Region, ProfessionSante

bp_accueil = Blueprint("accueil", __name__)

@bp_accueil.route("/")
@bp_accueil.route("/accueil")
@bp_accueil.route("/accueil.html")
def index():
    """Page d'accueil : affiche les régions et professions."""
    session = Session()
    try:
        regions     = session.query(Region).order_by(Region.libelle).all()
        professions = (session.query(ProfessionSante)
                              .order_by(ProfessionSante.libelle).all())
        return render_template("accueil.html",
                               regions=regions,
                               professions=professions)
    finally:
        session.close()


@bp_accueil.route("/pathologies")
@bp_accueil.route("/pathologies.html")
def pathologies():
    return render_template("pathologies.html")


@bp_accueil.route("/acces-soins")
@bp_accueil.route("/acces-soins.html")
def acces_soins():
    return render_template("acces-soins.html")


@bp_accueil.route("/professionnels")
@bp_accueil.route("/professionnels.html")
def professionnels():
    return render_template("professionnels.html")


@bp_accueil.route("/presentation")
@bp_accueil.route("/presentation.html")
def presentation():
    return render_template("presentation.html")

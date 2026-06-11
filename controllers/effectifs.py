from flask import Blueprint, render_template, request
from models.db import Session
from models.dimensions import ProfessionSante, Departement
from services.ameli_api import AmeliAPI

bp_effectifs = Blueprint("effectifs", __name__)

# Instance unique du service API (réutilise la session HTTP)
api = AmeliAPI()


@bp_effectifs.route("/effectifs")
def afficher():
    """Affiche les effectifs pour la sélection de l'utilisateur."""
    profession_id = request.args.get("profession_id", type=int)
    departement_id = request.args.get("departement_id", type=int)
    annee = request.args.get("annee", type=int)

    session = Session()
    try:
        prof = session.get(ProfessionSante, profession_id)
        dept = session.get(Departement, departement_id)

        # Vérification que tous les paramètres sont présents et valides
        if not prof or not dept or not annee:
            return render_template(
                "erreur.html",
                message="Paramètres manquants."
            ), 400

        # Appels à l'API ameli.fr
        resultats = api.get_effectifs(prof.libelle, dept.code, annee)
        evolution = api.get_evolution_effectifs(prof.libelle, dept.code)

        return render_template(
            "effectifs.html",
            prof=prof,
            dept=dept,
            annee=annee,
            resultats=resultats,
            evolution=evolution,
        )
    finally:
        session.close()

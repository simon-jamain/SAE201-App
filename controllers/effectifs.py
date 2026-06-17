from flask import Blueprint, render_template, request
from models.db import Session
from models.dimensions import ProfessionSante, Departement
from services.ameli_api import AmeliAPI

bp_effectifs = Blueprint("effectifs", __name__)
api = AmeliAPI()


@bp_effectifs.route("/effectifs")
def afficher():
    """Affiche les effectifs pour la sélection de l'utilisateur."""
    profession_id  = request.args.get("profession_id",  type=int)
    departement_id = request.args.get("departement_id", type=int)
    annee          = request.args.get("annee",          type=int)

    session = Session()
    try:
        prof = session.get(ProfessionSante, profession_id)
        dept = session.get(Departement,     departement_id)

        if not prof or not dept or not annee:
            return render_template(
                "erreur.html",
                code=400,
                message="Paramètres manquants. Veuillez remplir tous les champs du formulaire."
            ), 400

        if dept.code == "999":
            return render_template(
                "erreur.html",
                code=400,
                message="Veuillez sélectionner un département spécifique, pas 'FRANCE' (niveau national non supporté par l'API)."
            ), 400

        resultats = api.get_effectifs(prof.libelle, dept.code, annee)
        evolution  = api.get_evolution_effectifs(prof.libelle, dept.code)

        # None = erreur réseau vers l'API
        if resultats is None or evolution is None:
            return render_template(
                "erreur.html",
                type="api",
                message="L'API ameli.fr n'a pas répondu. Vérifiez votre connexion et réessayez."
            ), 503

        return render_template(
            "effectifs.html",
            prof=prof, dept=dept, annee=annee,
            resultats=resultats, evolution=evolution
        )
    finally:
        session.close()

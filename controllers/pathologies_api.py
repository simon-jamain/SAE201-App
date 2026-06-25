from flask import Blueprint, jsonify, request
from models.db import Session
from models.dimensions import Departement, Region
from services.ameli_api import AmeliAPI

bp_pathologies_api = Blueprint("pathologies_api", __name__, url_prefix="/api")

# Instance unique du service API (r├®utilise la session HTTP)
api = AmeliAPI()


def _annotate_pathology_labels(rows):
    """Ajoute les libellés lisibles des régions et départements aux lignes de pathologies."""
    if not rows:
        return rows

    session = Session()
    try:
        region_codes = {
            row["region"].zfill(2)
            for row in rows
            if row.get("region") and row["region"].isdigit()
        }
        dept_codes = {
            row["departement"]
            for row in rows
            if row.get("departement")
        }

        regions = {
            region.code: region.libelle
            for region in session.query(Region).filter(Region.code.in_(region_codes)).all()
        }
        depts = {
            departement.code: departement.libelle
            for departement in session.query(Departement).filter(Departement.code.in_(dept_codes)).all()
        }
    finally:
        session.close()

    for row in rows:
        row["region_libelle"] = regions.get(row.get("region"), row.get("region"))
        row["departement_libelle"] = depts.get(row.get("departement"), row.get("departement"))
    return rows


@bp_pathologies_api.route("/pathologies")
def pathologies():
    """Retourne des donnees de pathologies depuis l'API AMELI."""
    year = request.args.get("year", type=int)
    pathologie = request.args.get("pathologie", default="all", type=str)
    region = request.args.get("region", type=str)
    departement = request.args.get("departement", type=str)
    distinct = request.args.get("distinct")

    if distinct is not None:
        return jsonify(api.get_pathology_labels(annee=year))

    results = api.get_pathologies(
        annee=year,
        pathologie=pathologie,
        region=region,
        departement=departement,
    )
    return jsonify(_annotate_pathology_labels(results))

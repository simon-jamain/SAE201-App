from flask import Blueprint, jsonify, request
from models.db import Session
from models.dimensions import Departement, Region
from services.ameli_api import AmeliAPI

bp_api = Blueprint("api", __name__, url_prefix="/api")

# Instance unique du service API (réutilise la session HTTP)
api = AmeliAPI()


@bp_api.route("/regions")
def regions():
    """Retourne la liste des régions au format JSON."""
    session = Session()
    try:
        regions = session.query(Region).order_by(Region.code).all()
        return jsonify([
            {"id": r.id, "code": r.code, "libelle": r.libelle}
            for r in regions
        ])
    finally:
        session.close()


@bp_api.route("/departements/<int:region_id>")
def departements(region_id):
    """Retourne les départements d'une région au format JSON."""
    session = Session()
    try:
        depts = (
            session.query(Departement)
            .filter_by(region_id=region_id)
            .order_by(Departement.code)
            .all()
        )
        return jsonify([
            {"id": d.code, "code": d.code, "libelle": d.libelle}
            for d in depts
        ])
    finally:
        session.close()


def _annotate_pathology_labels(rows):
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


@bp_api.route("/pathologies")
def pathologies():
    """Retourne des données de pathologies depuis l'API AMELI."""
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

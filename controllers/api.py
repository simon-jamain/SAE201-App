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


@bp_api.route("/cache/info")
def cache_info():
    """Retourne les statistiques actuelles du cache ameli.fr."""
    return jsonify(AmeliAPI.cache_info())


@bp_api.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Vide le cache ameli.fr (forcer un rechargement des données)."""
    AmeliAPI.vider_cache()
    return jsonify({"status": "ok", "message": "Cache vidé avec succès."})


# Données de secours si le service AmeliAPI ne fournit pas encore les helpers
SAMPLE_PATHOLOGIES = [
    {"region": "Île-de-France", "pathologie": "Diabète", "annee": 2024, "nombre_patients": 542000, "taux_prevalence": 4.5, "departement": "75", "region_libelle": "Île-de-France", "departement_libelle": "Paris"},
    {"region": "Auvergne-Rhône-Alpes", "pathologie": "Diabète", "annee": 2024, "nombre_patients": 398000, "taux_prevalence": 5.1, "departement": "69", "region_libelle": "Auvergne-Rhône-Alpes", "departement_libelle": "Rhône"},
    {"region": "Nouvelle-Aquitaine", "pathologie": "Hypertension artérielle", "annee": 2023, "nombre_patients": 723000, "taux_prevalence": 12.3, "departement": "33", "region_libelle": "Nouvelle-Aquitaine", "departement_libelle": "Gironde"},
    {"region": "Occitanie", "pathologie": "Asthme", "annee": 2024, "nombre_patients": 334000, "taux_prevalence": 5.8, "departement": "31", "region_libelle": "Occitanie", "departement_libelle": "Haute-Garonne"},
]


@bp_api.route("/pathologies")
def pathologies():
    """Retourne des données de pathologies — essaie d'utiliser `AmeliAPI` si disponible."""
    year = request.args.get("year", type=int)
    pathologie = request.args.get("pathologie", default="all", type=str)
    region = request.args.get("region", type=str)
    departement = request.args.get("departement", type=str)
    distinct = request.args.get("distinct")

    # distinct -> libellés
    if distinct is not None:
        if hasattr(api, "get_pathology_labels"):
            return jsonify(api.get_pathology_labels(annee=year))
        return jsonify(sorted({r["pathologie"] for r in SAMPLE_PATHOLOGIES}))

    # Si AmeliAPI expose une méthode pour récupérer les pathologies, l'utiliser
    if hasattr(api, "get_pathologies"):
        results = api.get_pathologies(
            annee=year,
            pathologie=pathologie,
            region=region,
            departement=departement,
        )
        return jsonify(_annotate_pathology_labels(results))

    # Sinon, fallback sur les données sample avec filtres
    results = SAMPLE_PATHOLOGIES
    if year:
        results = [r for r in results if r.get("annee") == year]
    if pathologie and pathologie != "all":
        results = [r for r in results if r.get("pathologie") == pathologie]
    if region and region != "all":
        results = [r for r in results if str(r.get("region")) == str(region) or str(r.get("region_libelle")) == str(region)]
    if departement and departement != "all":
        results = [r for r in results if str(r.get("departement")) == str(departement) or str(r.get("departement_libelle")) == str(departement)]

    return jsonify(results)

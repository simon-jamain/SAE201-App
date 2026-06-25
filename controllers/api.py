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
            {"id": d.id, "code": d.code, "libelle": d.libelle}
            for d in depts
        ])
    finally:
        session.close()


@bp_api.route("/cache/info")
def cache_info():
    """Retourne les statistiques actuelles du cache ameli.fr."""
    return jsonify(AmeliAPI.cache_info())


@bp_api.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Vide le cache ameli.fr (forcer un rechargement des données)."""
    AmeliAPI.vider_cache()
    return jsonify({"status": "ok", "message": "Cache vidé avec succès."})



# controllers/honoraires.py
from flask import Blueprint, render_template, request
from models.db import Session
from models.dimensions import ProfessionSante, Departement, Region
from services.ameli_api import AmeliAPI

bp_honoraires = Blueprint("honoraires", __name__)
api = AmeliAPI()

ANNEES_DISPONIBLES = list(range(2024, 2014, -1))  # 2024 → 2015

# Types d'honoraires proposés pour la comparaison (niveau 1, niveau 2 nul)
# Correspond aux ids 1, 16, 17, 19 de la table type_honoraire
TYPES_COMPARAISON = [
    "Ensemble des honoraires",
    "Actes",
    "Dépassements",
    "Rémunérations forfaitaires",
]

# Visualisations valides — sert à filtrer un viz_type douteux venu de l'URL
VIZ_VALIDES = {"tableau", "courbe"}

# Professions à exclure du select (données incomplètes dans le dataset honoraires)
PROFESSIONS_EXCLUES_HONORAIRES = {
    "Autres médecins",
    "Ensemble des auxiliaires médicaux",
    "Ensemble des chirurgiens-dentistes",
    "Ensemble des médecins",
    "Ensemble des médecins généralistes",
    "Ensemble des médecins spécialistes (hors généralistes)",
}


# ── Mise en forme des données pour les graphiques ───────────────────────────
# On prépare ici (contrôleur) la structure exacte attendue par Chart.js, pour
# que le template n'ait plus aucune logique de transformation (dédoublonnage,
# parseFloat, etc.). La vue se contente de brancher labels/series sur Chart.js.

def _serie_comparaison(raw):
    """Transforme les lignes brutes de l'API en {labels, series} pour la courbe.

    labels : liste d'années (str), triées.
    series : une entrée par département, avec son libellé et ses montants
             alignés sur labels (None si l'année manque).
    """
    annees = sorted({str(r.get("annee")) for r in raw})

    # Ordre d'apparition des départements, sans doublon
    depts = []
    for r in raw:
        code = r.get("departement")
        if code and all(d["code"] != code for d in depts):
            depts.append({
                "code": code,
                "libelle": r.get("libelle_departement") or code,
            })

    series = []
    for d in depts:
        lignes = [r for r in raw if r.get("departement") == d["code"]]
        data = []
        for a in annees:
            ligne = next((x for x in lignes if str(x.get("annee")) == a), None)
            valeur = None
            if ligne is not None:
                try:
                    valeur = float(ligne.get("montant_honoraires_moyens"))
                except (TypeError, ValueError):
                    valeur = None
            data.append(valeur)
        series.append({"label": d["libelle"], "data": data})

    return {"labels": annees, "series": series}


@bp_honoraires.route("/honoraires")
@bp_honoraires.route("/honoraires.html")
def afficher():
    # ── Paramètres communs ───────────────────────────────────────────────
    profession_id  = request.args.get("profession_id",  type=int)
    departement_id = request.args.get("departement_id", type=int)
    annee          = request.args.get("annee",          type=int)
    region_id      = request.args.get("region_id",      type=int)
    viz_type       = request.args.get("viz_type", default="tableau", type=str)
    if viz_type not in VIZ_VALIDES:
        viz_type = "tableau"

    # ── Paramètres analyse 1 (comparaison / courbe) ─────────────────────
    departement_id_2 = request.args.get("departement_id_2", type=int)
    region_id_2      = request.args.get("region_id_2",      type=int)
    type_honoraires  = request.args.get("type_honoraires",
                                        default="Ensemble des honoraires", type=str)

    session = Session()
    try:
        # ── Listes pour les <select> (depuis MySQL) ──────────────────────
        regions     = session.query(Region).order_by(Region.libelle).all()
        professions = [
            p for p in session.query(ProfessionSante).order_by(ProfessionSante.libelle).all()
            if p.libelle not in PROFESSIONS_EXCLUES_HONORAIRES
        ]

        departements = []
        if region_id:
            departements = (
                session.query(Departement)
                .filter_by(region_id=region_id)
                .order_by(Departement.code).all()
            )

        departements_2 = []
        if region_id_2:
            departements_2 = (
                session.query(Departement)
                .filter_by(region_id=region_id_2)
                .order_by(Departement.code).all()
            )

        # ── Données API : on ne récupère QUE la visualisation demandée ────
        # (avant, les 4-5 méthodes étaient appelées à chaque affichage)
        classement        = []        # tableau : classement départements
        comparaison       = []        # courbe  : lignes brutes
        chart_courbe      = None      # courbe  : {labels, series} prêt pour Chart.js
        prof  = None
        dept  = None
        dept2 = None

        if profession_id and annee:
            prof = session.get(ProfessionSante, profession_id)
            if not prof:
                return render_template("erreur.html",
                    message="Profession introuvable."), 400

        if profession_id and departement_id and annee:
            dept = session.get(Departement, departement_id)
            if not dept:
                return render_template("erreur.html",
                    message="Département introuvable."), 400

        if prof:
            if viz_type == "tableau":
                # Le tableau n'affiche que le classement (profession + année)
                classement = api.get_classement_departements(prof.libelle, annee)

            elif viz_type == "courbe":
                if dept and departement_id_2:
                    dept2 = session.get(Departement, departement_id_2)
                    if dept2:
                        comparaison = api.get_evolution_comparaison(
                            prof.libelle, dept.code, dept2.code, type_honoraires
                        )
                        chart_courbe = _serie_comparaison(comparaison)

        return render_template(
            "honoraires.html",
            # Listes filtres
            regions=regions,
            professions=professions,
            departements=departements,
            departements_2=departements_2,
            annees=ANNEES_DISPONIBLES,
            types_comparaison=TYPES_COMPARAISON,
            # Valeurs sélectionnées
            region_id=region_id,
            region_id_2=region_id_2,
            profession_id=profession_id,
            departement_id=departement_id,
            departement_id_2=departement_id_2,
            annee=annee,
            viz_type=viz_type,
            type_honoraires=type_honoraires,
            # Données API
            prof=prof,
            dept=dept,
            dept2=dept2,
            classement=classement,
            comparaison=comparaison,
            # Données prêtes pour Chart.js (mises en forme côté contrôleur)
            chart_courbe=chart_courbe,
        )
    finally:
        session.close()
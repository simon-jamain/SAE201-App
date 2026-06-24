# controllers/honoraires.py

# ── Imports ──────────────────────────────────────────────────────────────────
from flask import Blueprint, render_template, request
# Blueprint      : permet de regrouper les routes liées aux honoraires dans un module indépendant
# render_template: charge et retourne un template Jinja2 (fichier HTML)
# request        : objet Flask donnant accès aux paramètres de l'URL (query string)

from models.db import Session                                        # fabrique de sessions SQLAlchemy pour accéder à la base de données
from models.dimensions import ProfessionSante, Departement, Region  # modèles ORM utilisés pour remplir les listes des formulaires
from services.ameli_api import AmeliAPI                              # classe de service centralisant tous les appels à l'API data.ameli.fr

bp_honoraires = Blueprint("honoraires", __name__)  # déclare le Blueprint nommé "honoraires", rattaché à ce module
api = AmeliAPI()                                   # instance unique de AmeliAPI partagée par toutes les requêtes de ce Blueprint

ANNEES_DISPONIBLES = list(range(2024, 2014, -1))   # génère la liste [2024, 2023, ..., 2015] pour remplir le select d'année

# Types d'honoraires proposés pour la comparaison (niveau 1, niveau 2 nul)
# Correspond aux ids 1, 16, 17, 19 de la table type_honoraire
TYPES_COMPARAISON = [
    "Ensemble des honoraires",     # total de tous les honoraires
    "Actes",                       # honoraires liés aux actes médicaux uniquement
    "Dépassements",                # dépassements d'honoraires (secteur 2 et 3)
    "Rémunérations forfaitaires",  # rémunérations non liées aux actes (forfaits, primes)
]

# Visualisations valides — sert à filtrer un viz_type douteux venu de l'URL
VIZ_VALIDES = {"tableau", "courbe"}  # ensemble Python (lookup O(1)) contenant les deux seules valeurs acceptées pour viz_type

# Professions à exclure du select (données incomplètes dans le dataset honoraires)
PROFESSIONS_EXCLUES_HONORAIRES = {
    # Ces libellés correspondent à des agrégats de professions
    # dont les données honoraires sont incomplètes ou non pertinentes à afficher
    "Autres médecins",
    "Ensemble des auxiliaires médicaux",
    "Ensemble des chirurgiens-dentistes",
    "Ensemble des médecins",
    "Ensemble des médecins généralistes",
    "Ensemble des médecins spécialistes (hors généralistes)",
}


# ── Mise en forme des données pour les graphiques ───────────────────────────
# La structure exacte attendue par Chart.js est préparée ici dans le contrôleur,
# pour que le template n'ait aucune logique de transformation à effectuer.
# La vue se contente de brancher labels/series sur Chart.js.

def _serie_comparaison(raw):
    """Transforme les lignes brutes de l'API en {labels, series} pour la courbe.

    labels : liste d'années (str), triées.
    series : une entrée par département, avec son libellé et ses montants
             alignés sur labels (None si l'année manque).
    """
    annees = sorted({str(r.get("annee")) for r in raw})  # collecte toutes les années présentes dans les données et les trie chronologiquement (set pour dédoublonner)

    # Ordre d'apparition des départements, sans doublon
    depts = []
    for r in raw:
        code = r.get("departement")                              # récupère le code département de chaque enregistrement
        if code and all(d["code"] != code for d in depts):      # n'ajoute le département que s'il n'est pas encore dans la liste (préserve l'ordre d'apparition)
            depts.append({
                "code": code,
                "libelle": r.get("libelle_departement") or code, # utilise le libellé si disponible, sinon retombe sur le code comme valeur d'affichage
            })

    series = []
    for d in depts:                                                         # pour chaque département présent dans les données
        lignes = [r for r in raw if r.get("departement") == d["code"]]     # filtre les enregistrements appartenant à ce département
        data = []
        for a in annees:                                                    # pour chaque année disponible dans l'ordre trié
            ligne = next((x for x in lignes if str(x.get("annee")) == a), None)  # cherche l'enregistrement correspondant à cette année pour ce département (None si l'année manque)
            valeur = None
            if ligne is not None:
                try:
                    valeur = float(ligne.get("montant_honoraires_moyens"))  # convertit le montant en float pour Chart.js (l'API peut renvoyer une chaîne)
                except (TypeError, ValueError):
                    valeur = None                                            # si la conversion échoue, on met None : Chart.js gère les trous avec spanGaps
            data.append(valeur)                                             # aligne le montant sur l'axe des années (None = point manquant sur la courbe)
        series.append({"label": d["libelle"], "data": data})               # ajoute la série du département avec son libellé et ses montants alignés

    return {"labels": annees, "series": series}  # retourne la structure directement exploitable par Chart.js


@bp_honoraires.route("/honoraires")
@bp_honoraires.route("/honoraires.html")          # double route pour compatibilité avec les liens existants
def afficher():
    # ── Paramètres communs ───────────────────────────────────────────────
    profession_id  = request.args.get("profession_id",  type=int)   # identifiant de la profession sélectionnée (clé primaire de ProfessionSante)
    departement_id = request.args.get("departement_id", type=int)   # identifiant du département principal (clé primaire de Departement)
    annee          = request.args.get("annee",          type=int)   # année sélectionnée pour le filtrage
    region_id      = request.args.get("region_id",      type=int)   # identifiant de la région principale, utilisé pour charger les départements du select
    viz_type       = request.args.get("viz_type", default="tableau", type=str)  # type de visualisation demandé ("tableau" ou "courbe"), "tableau" par défaut
    if viz_type not in VIZ_VALIDES:
        viz_type = "tableau"                        # si la valeur reçue est invalide (manipulation URL), on retombe sur "tableau"

    # ── Paramètres spécifiques à la visualisation courbe ────────────────
    departement_id_2 = request.args.get("departement_id_2", type=int)              # identifiant du second département à comparer (courbe uniquement)
    region_id_2      = request.args.get("region_id_2",      type=int)              # identifiant de la région du second département, pour charger son select
    type_honoraires  = request.args.get("type_honoraires",
                                        default="Ensemble des honoraires", type=str)  # type d'honoraires à comparer sur la courbe, "Ensemble des honoraires" par défaut

    session = Session()  # ouvre une session SQLAlchemy
    try:
        # ── Listes pour les <select> (depuis MySQL) ──────────────────────
        regions     = session.query(Region).order_by(Region.libelle).all()  # toutes les régions triées alphabétiquement pour le select région
        professions = [
            p for p in session.query(ProfessionSante).order_by(ProfessionSante.libelle).all()
            if p.libelle not in PROFESSIONS_EXCLUES_HONORAIRES              # exclut les professions agrégées dont les données sont incomplètes dans le dataset Ameli
        ]

        departements = []
        if region_id:                                                        # ne charge les départements que si une région a été sélectionnée
            departements = (
                session.query(Departement)
                .filter_by(region_id=region_id)
                .order_by(Departement.code).all()                           # départements de la région principale triés par code pour le premier select département
            )

        departements_2 = []
        if region_id_2:                                                      # même logique pour le second sélecteur de comparaison
            departements_2 = (
                session.query(Departement)
                .filter_by(region_id=region_id_2)
                .order_by(Departement.code).all()                           # départements de la région secondaire pour le second select département
            )

        # ── Données API : uniquement la visualisation demandée ────────────
        classement   = []    # résultats du tableau : liste des départements classés par montant moyen
        comparaison  = []    # résultats bruts de la courbe : enregistrements retournés par l'API
        chart_courbe = None  # données mises en forme pour Chart.js ({labels, series}), None si la courbe n'est pas demandée
        prof  = None         # objet ProfessionSante correspondant à profession_id
        dept  = None         # objet Departement correspondant à departement_id
        dept2 = None         # objet Departement correspondant à departement_id_2

        if profession_id and annee:                                          # profession + année sont les paramètres minimums pour tout appel API
            prof = session.get(ProfessionSante, profession_id)              # récupère l'objet ProfessionSante par sa clé primaire
            if not prof:
                return render_template("erreur.html",
                    message="Profession introuvable."), 400                 # retourne HTTP 400 si l'identifiant ne correspond à aucune profession en base

        if profession_id and departement_id and annee:                      # un département est requis en plus pour les visualisations qui en dépendent
            dept = session.get(Departement, departement_id)                 # récupère l'objet Departement par sa clé primaire
            if not dept:
                return render_template("erreur.html",
                    message="Département introuvable."), 400                # retourne HTTP 400 si l'identifiant ne correspond à aucun département en base

        if prof:                                                             # n'appelle l'API que si la profession a été trouvée en base
            if viz_type == "tableau":
                classement = api.get_classement_departements(prof.libelle, annee)  # interroge l'API pour obtenir tous les départements classés par montant moyen pour cette profession et cette année

            elif viz_type == "courbe":
                if dept and departement_id_2:                               # la courbe nécessite obligatoirement les deux départements
                    dept2 = session.get(Departement, departement_id_2)     # récupère le second département par sa clé primaire
                    if dept2:                                               # n'appelle l'API que si le second département existe en base
                        comparaison = api.get_evolution_comparaison(
                            prof.libelle, dept.code, dept2.code, type_honoraires  # interroge l'API pour l'évolution comparée des deux départements sur le type d'honoraires choisi
                        )
                        chart_courbe = _serie_comparaison(comparaison)     # transforme les données brutes en structure {labels, series} prête pour Chart.js

        return render_template(
            "honoraires.html",
            # Listes filtres
            regions=regions,                         # toutes les régions pour le select région principal
            professions=professions,                 # professions filtrées pour le select profession
            departements=departements,               # départements de la région principale pour le select département principal
            departements_2=departements_2,           # départements de la région secondaire pour le select département de comparaison
            annees=ANNEES_DISPONIBLES,               # liste des années disponibles pour le select année
            types_comparaison=TYPES_COMPARAISON,     # types d'honoraires disponibles pour le select type (courbe uniquement)
            # Valeurs sélectionnées (pour pré-remplir les selects après soumission)
            region_id=region_id,
            region_id_2=region_id_2,
            profession_id=profession_id,
            departement_id=departement_id,
            departement_id_2=departement_id_2,
            annee=annee,
            viz_type=viz_type,                       # type de visualisation actif, utilisé par honoraires.js pour afficher ou masquer les bons filtres
            type_honoraires=type_honoraires,
            # Objets ORM résolus (pour afficher les libellés dans la page)
            prof=prof,                               # objet ProfessionSante sélectionné, utilisé pour afficher le nom de la profession dans les titres
            dept=dept,                               # objet Departement principal sélectionné
            dept2=dept2,                             # objet Departement secondaire sélectionné (courbe uniquement)
            # Données API
            classement=classement,                   # liste des départements classés par montant moyen (tableau uniquement)
            comparaison=comparaison,                 # données brutes de l'API (courbe uniquement)
            # Données prêtes pour Chart.js (mises en forme côté contrôleur)
            chart_courbe=chart_courbe,               # dictionnaire {labels, series} injecté en JSON dans le template pour être lu par honoraires.js
        )
    finally:
        session.close()  # ferme la session SQLAlchemy dans tous les cas (succès ou exception)
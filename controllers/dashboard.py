from flask import Blueprint, render_template, request
from models.db import Session
from models.dimensions import ProfessionSante, Departement, Region, PostePrescription
from services.ameli_api import AmeliAPI

# Blueprint Flask regroupant les routes du tableau de bord
bp_dashboard = Blueprint("dashboard", __name__)
api = AmeliAPI()  # Instance unique du client API Ameli

FRANCE_REGION_CODE = "999"
FRANCE_REGION_LABEL = "france"

# Mots-clés permettant d'identifier si une profession est médicale (médecin)
MOTS_MEDECIN = ["médecin", "généraliste", "generaliste", "cardiologue",
                "dermatologue", "gynécologue", "ophtalmologue", "pédiatre",
                "psychiatre", "radiologue", "chirurgien", "neurologue",
                "rhumatologue", "urologue", "gastroentérologue", "anesthésiste",
                "endocrinologue", "pneumologue", "néphrologue"]

PROFESSIONS_PRESCRIPTION_EXCLUES = {
    "Autres médecins",
    "Ensemble des auxiliaires médicaux",
    "Ensemble des chirurgiens-dentistes",
    "Ensemble des médecins",
    "Ensemble des médecins généralistes",
    "Ensemble des médecins spécialistes (hors généralistes)",
}


def _est_medecin(libelle):
    """Retourne True si le libellé de profession contient un mot-clé médical."""
    return any(mot in libelle.lower() for mot in MOTS_MEDECIN)


def _get_listes(session):
    """
    Charge depuis la base les listes de référence nécessaires aux filtres
    des formulaires (régions, professions, postes de prescription).
    """
    # On retire l'entrée agrégée "France" pour ne garder que les vraies régions utilisables.
    regions     = [
        region for region in session.query(Region).order_by(Region.libelle).all()
        if str(region.code).strip() != FRANCE_REGION_CODE
        and str(region.libelle).strip().lower() != FRANCE_REGION_LABEL
    ]
    professions = session.query(ProfessionSante).order_by(ProfessionSante.libelle).all()
    postes      = session.query(PostePrescription).order_by(PostePrescription.id).all()
    return regions, professions, postes


def _get_departements_par_region(session, region_id):
    """Charge les départements d'une région pour pré-remplir le formulaire."""
    if not region_id:
        return []
    return (
        session.query(Departement)
        .filter_by(region_id=region_id)
        .order_by(Departement.code)
        .all()
    )


def _filtrer_professions_prescription(professions):
    """Retire les catégories de professions non pertinentes pour la prescription."""
    return [p for p in professions if p.libelle not in PROFESSIONS_PRESCRIPTION_EXCLUES]

#  Route : /medicaments

@bp_dashboard.route("/medicaments")
def medicaments():
    """Affiche les indicateurs de prescriptions avec filtres de profession, territoire, année et poste."""
    session = Session()
    try:
        regions, professions, postes = _get_listes(session)
        professions = _filtrer_professions_prescription(professions)

        # Récupération des paramètres de filtrage passés en query string
        profession_id  = request.args.get("profession_id",  type=int)
        departement_id = request.args.get("departement_id", type=int)
        region_id      = request.args.get("region_id",      type=int)
        annee          = request.args.get("annee",           type=int)
        poste_id       = request.args.get("poste_id",       type=int)

        # Affichage du formulaire vide si aucune profession n'est sélectionnée
        if not profession_id:
            return render_template("prescription.html",
                                   regions=regions, professions=professions, postes=postes)

        # Résolution des entités à partir des IDs reçus
        prof  = session.get(ProfessionSante, profession_id)
        dept  = session.get(Departement, departement_id) if departement_id else None
        poste = session.get(PostePrescription, poste_id) if poste_id else None

        # Construction de la clause WHERE pour la requête tableau (données détaillées)
        # et pour la requête courbe (évolution temporelle)
        where_courbe  = f"profession_sante=\"{prof.libelle}\""
        if annee:
            # Si une année est choisie, on filtre dessus pour le tableau
            where_tableau = f"annee=date'{annee}' AND profession_sante=\"{prof.libelle}\""
        else:
            # Sans année, le tableau couvre toutes les années disponibles
            where_tableau = f"profession_sante=\"{prof.libelle}\""

        # Ajout optionnel du filtre géographique (département)
        if dept:
            code_dept = str(dept.code).strip()
            where_tableau += f' AND departement="{code_dept}"'
            where_courbe  += f' AND departement="{code_dept}"'

        # Ajout optionnel du filtre par poste de prescription
        if poste:
            where_tableau += f' AND poste_prescription="{poste.id}"'
            where_courbe  += f' AND poste_prescription="{poste.id}"'

        # Appel API pour les données tabulaires (montants et postes par année)
        donnees_api = api._requete("prescriptions", {
            "select": "annee, poste_prescription, libelle_poste_prescription, montant_total_prescription_integer, montant_moyen_prescription_integer",
            "where":  where_tableau,
            "limit":  100
        })

        # Appel API pour les données d'évolution temporelle (courbe)
        donnees_evolution = api._requete("prescriptions", {
            "select": "annee, montant_total_prescription_integer, montant_moyen_prescription_integer",
            "where":  where_courbe,
            "limit":  100
        })

        # Gestion des erreurs API : affichage d'une page d'erreur dédiée
        if donnees_api is None or donnees_evolution is None:
            return render_template("erreur.html", type="api",
                message="L'API data.ameli.fr n'a pas répondu ou aucun résultat ne correspond."), 503

        # Normalisation des résultats tabulaires
        resultats = []
        for r in donnees_api:
            annee_brute = r.get("annee")
            resultats.append({
                "annee":            int(annee_brute[:4]) if annee_brute else annee,
                "poste":            r.get("libelle_poste_prescription") or "Inconnu",
                "nb_prescriptions": r.get("montant_moyen_prescription_integer") or 0,
                "montant_total":    r.get("montant_total_prescription_integer") or 0
            })
        resultats.sort(key=lambda x: x["annee"])

        # Agrégation des données d'évolution par année
        # (plusieurs lignes API peuvent correspondre à la même année → on cumule)
        evolution_dict = {}
        for r in donnees_evolution:
            annee_brute = r.get("annee")
            annee_key   = int(annee_brute[:4]) if annee_brute else annee
            if annee_key not in evolution_dict:
                evolution_dict[annee_key] = {"annee": annee_key, "nb_prescriptions": 0, "montant_total": 0}
            evolution_dict[annee_key]["nb_prescriptions"] += int(r.get("montant_moyen_prescription_integer") or 0)
            evolution_dict[annee_key]["montant_total"]    += float(r.get("montant_total_prescription_integer") or 0)

        # Tri chronologique de l'évolution pour l'affichage en courbe
        evolution = sorted(evolution_dict.values(), key=lambda x: x["annee"])

        # Calcul des totaux affichés en résumé dans le template
        total_boites  = sum(int(r["nb_prescriptions"])  for r in resultats)
        total_montant = sum(float(r["montant_total"])    for r in resultats)

        return render_template("prescription.html",
                               regions=regions, professions=professions, postes=postes,
                               prof=prof, dept=dept, annee=annee,
                               poste_id=poste_id, poste=poste,
                               resultats=resultats, evolution=evolution,
                               total_boites=total_boites, total_montant=total_montant)
    finally:
        # La session SQLAlchemy est toujours fermée, même en cas d'exception
        session.close()


# ─────────────────────────────────────────────
#  Route : /pathologies  (stub)
# ─────────────────────────────────────────────
@bp_dashboard.route("/pathologies")
def pathologies():
    """Page de visualisation des pathologies — pas encore implémentée."""
    return render_template("pathologies.html")


# ─────────────────────────────────────────────
#  Route : /professionnels
# ─────────────────────────────────────────────
@bp_dashboard.route("/professionnels")
def professionnels():
    """Affiche les effectifs des professionnels de santé selon le territoire, l'année et la profession."""
    session = Session()
    try:
        regions, professions, postes = _get_listes(session)

        # Filtres reçus en query string
        profession_id  = request.args.get("profession_id",  type=int)
        departement_id = request.args.get("departement_id", type=int)
        region_id      = request.args.get("region_id",      type=int)
        annee          = request.args.get("annee",           type=int)

        # Résolution anticipée pour pouvoir réafficher les filtres tels qu'ils ont été choisis
        prof = session.get(ProfessionSante, profession_id) if profession_id else None
        dept = session.get(Departement, departement_id) if departement_id else None
        reg  = session.get(Region,      region_id)      if region_id      else (dept.region if dept else None)

        if not region_id and dept and dept.region_id:
            region_id = dept.region_id

        departements = _get_departements_par_region(session, region_id)

        # Formulaire vide si profession + année + territoire ne sont pas tous renseignés
        if not all([profession_id, annee]) or not (departement_id or region_id):
            return render_template("professionnels.html",
                                   regions=regions, professions=professions,
                                   reg=reg, dept=dept,
                                   region_id=region_id, departement_id=departement_id,
                                   departements=departements,
                                   annee=annee)

        if not prof:
            return render_template("erreur.html", code=400, message="Paramètres invalides."), 400

        # Codes territoire et libellé affiché dans le template
        dept_code        = dept.code if dept else None
        region_code      = reg.code  if reg  else None
        territoire_label = f"{dept.code} – {dept.libelle}" if dept else (reg.libelle if reg else "")

        # Quatre appels API parallèles (séquentiels ici) pour alimenter les graphiques
        resultats = api.get_effectifs(prof.libelle, dept_code or "999", annee) if dept_code else []
        evolution = api.get_evolution_effectifs(prof.libelle, dept_code, region_code)
        par_sexe  = api.get_effectifs_par_sexe(prof.libelle, dept_code, annee, region_code)
        par_age   = api.get_effectifs_par_age(prof.libelle, dept_code, annee, region_code)

        if evolution is None:
            return render_template("erreur.html", type="api",
                message="L'API ameli.fr n'a pas répondu. Réessayez dans quelques instants."), 503

        return render_template("professionnels.html",
                               regions=regions, professions=professions,
                               prof=prof, dept=dept, reg=reg,
                               territoire_label=territoire_label,
                               annee=annee,
                               region_id=region_id,
                               departement_id=departement_id,
                               departements=departements,
                               resultats=resultats or [],
                               evolution=evolution or [],
                               par_sexe=par_sexe or [],
                               par_age=par_age or [])
    finally:
        session.close()
from flask import Blueprint, render_template, request
from models.db import Session
from models.dimensions import ProfessionSante, Departement, Region, PostePrescription
from services.ameli_api import AmeliAPI

bp_dashboard = Blueprint("dashboard", __name__)
api = AmeliAPI()

MOTS_MEDECIN = ["médecin", "généraliste", "generaliste", "cardiologue",
                "dermatologue", "gynécologue", "ophtalmologue", "pédiatre",
                "psychiatre", "radiologue", "chirurgien", "neurologue",
                "rhumatologue", "urologue", "gastroentérologue", "anesthésiste",
                "endocrinologue", "pneumologue", "néphrologue"]


def _est_medecin(libelle):
    return any(mot in libelle.lower() for mot in MOTS_MEDECIN)


def _get_listes(session):
    regions     = session.query(Region).order_by(Region.libelle).all()
    professions = session.query(ProfessionSante).order_by(ProfessionSante.libelle).all()
    postes      = session.query(PostePrescription).order_by(PostePrescription.id).all()
    return regions, professions, postes


@bp_dashboard.route("/medicaments")
def medicaments():
    session = Session()
    try:
        regions, professions, postes = _get_listes(session)

        profession_id  = request.args.get("profession_id",  type=int)
        departement_id = request.args.get("departement_id", type=int)
        region_id      = request.args.get("region_id",      type=int)
        annee          = request.args.get("annee",           type=int, default=2023)
        poste_id       = request.args.get("poste_id",       type=int)

        # Formulaire non soumis
        if not all([profession_id, departement_id]):
            return render_template("prescription.html",
                                   regions=regions, professions=professions, postes=postes)

        prof  = session.get(ProfessionSante, profession_id)
        dept  = session.get(Departement, departement_id)
        poste = session.get(PostePrescription, poste_id) if poste_id else None

        code_dept = str(dept.code).strip()

        where_tableau = f"annee=date'{annee}' AND departement=\"{code_dept}\" AND profession_sante=\"{prof.libelle}\""
        where_courbe  = f"departement=\"{code_dept}\" AND profession_sante=\"{prof.libelle}\""

        if poste:
            where_tableau += f' AND poste_prescription="{poste.id}"'
            where_courbe  += f' AND poste_prescription="{poste.id}"'

        donnees_api = api._requete("prescriptions", {
            "select": "annee, poste_prescription, libelle_poste_prescription, montant_total_prescription_integer, montant_moyen_prescription_integer",
            "where":  where_tableau,
            "limit":  100
        })

        donnees_evolution = api._requete("prescriptions", {
            "select": "annee, montant_total_prescription_integer, montant_moyen_prescription_integer",
            "where":  where_courbe,
            "limit":  100
        })

        if donnees_api is None or donnees_evolution is None:
            return render_template("erreur.html", type="api",
                message="L'API data.ameli.fr n'a pas répondu ou aucun résultat ne correspond."), 503

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

        evolution_dict = {}
        for r in donnees_evolution:
            annee_brute = r.get("annee")
            annee_key   = int(annee_brute[:4]) if annee_brute else annee
            if annee_key not in evolution_dict:
                evolution_dict[annee_key] = {"annee": annee_key, "nb_prescriptions": 0, "montant_total": 0}
            evolution_dict[annee_key]["nb_prescriptions"] += int(r.get("montant_moyen_prescription_integer") or 0)
            evolution_dict[annee_key]["montant_total"]    += float(r.get("montant_total_prescription_integer") or 0)

        evolution = sorted(evolution_dict.values(), key=lambda x: x["annee"])

        total_boites  = sum(int(r["nb_prescriptions"])  for r in resultats)
        total_montant = sum(float(r["montant_total"])    for r in resultats)

        return render_template("prescription.html",
                               regions=regions, professions=professions, postes=postes,
                               prof=prof, dept=dept, annee=annee,
                               poste_id=poste_id, poste=poste,
                               resultats=resultats, evolution=evolution,
                               total_boites=total_boites, total_montant=total_montant)
    finally:
        session.close()


@bp_dashboard.route("/professionnels")
def professionnels():
    session = Session()
    try:
        regions, professions, postes = _get_listes(session)

        profession_id  = request.args.get("profession_id",  type=int)
        departement_id = request.args.get("departement_id", type=int)
        region_id      = request.args.get("region_id",      type=int)
        annee          = request.args.get("annee",           type=int)

        if not all([profession_id, annee]) or not (departement_id or region_id):
            return render_template("professionnels.html",
                                   regions=regions, professions=professions)

        prof = session.get(ProfessionSante, profession_id)
        dept = session.get(Departement, departement_id) if departement_id else None
        reg  = session.get(Region,      region_id)      if region_id      else None

        if not prof:
            return render_template("erreur.html", code=400, message="Paramètres invalides."), 400

        dept_code        = dept.code if dept else None
        region_code      = reg.code  if reg  else None
        territoire_label = f"{dept.code} – {dept.libelle}" if dept else (reg.libelle if reg else "")

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
                               resultats=resultats or [],
                               evolution=evolution or [],
                               par_sexe=par_sexe or [],
                               par_age=par_age or [])
    finally:
        session.close()


@bp_dashboard.route("/accueil")
def accueil():
    """Rendu de la page d'accueil depuis le dashboard."""
    session = Session()
    try:
        regions, professions, postes = _get_listes(session)
        return render_template("accueil.html", regions=regions, professions=professions)
    finally:
        session.close()


@bp_dashboard.route("/pathologies")
def pathologies():
    """Page de visualisation des pathologies."""
    return render_template("pathologies.html")
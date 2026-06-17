from flask import Blueprint, render_template, request
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        annee          = request.args.get("annee",           type=int)
        poste_id       = request.args.get("poste_id",       type=int)

        # Formulaire non soumis : seule la profession est obligatoire
        if not profession_id:
            return render_template("prescription.html",
                                   regions=regions, professions=professions, postes=postes)

        prof  = session.get(ProfessionSante, profession_id)
        dept  = session.get(Departement, departement_id) if departement_id else None
        reg   = session.get(Region, region_id) if region_id else None
        poste = session.get(PostePrescription, poste_id) if poste_id else None

        # ---------------------------------------------------------------
        # LOGIQUE MODES :
        #   Mode A — Département sélectionné  → toutes les années,
        #                                        tableau : Année | Poste | Volume | Montant
        #   Mode B — Région seulement          → une année obligatoire,
        #                                        tableau : Département | Poste | Volume | Montant
        # ---------------------------------------------------------------
        if dept:
            # MODE A : un seul département
            # → année optionnelle : si choisie on filtre, sinon toutes les années
            mode               = "dept"
            depts_a_interroger = [dept]
            annee_filtre_tab   = annee  # None = toutes les années
        elif reg:
            # MODE B : région entière, une année obligatoire
            mode = "region"
            if not annee:
                return render_template("prescription.html",
                                       regions=regions, professions=professions, postes=postes,
                                       erreur_filtre="Veuillez sélectionner une année pour afficher les données par département.")
            annee_filtre_tab = annee
            depts_a_interroger = (
                session.query(Departement)
                .filter(Departement.region_id == reg.id)
                .order_by(Departement.code)
                .all()
            )
        else:
            return render_template("prescription.html",
                                   regions=regions, professions=professions, postes=postes,
                                   erreur_filtre="Veuillez sélectionner au moins une région.")

        def _requete_dept(d):
            """Effectue les deux requêtes API pour un département donné."""
            code = str(d.code).strip()
            where_tab = f'profession_sante="{prof.libelle}" AND departement="{code}"'
            where_evo = f'profession_sante="{prof.libelle}" AND departement="{code}"'

            # Filtre année si défini (obligatoire en mode région, optionnel en mode département)
            if annee_filtre_tab:
                where_tab += f" AND annee=date'{annee_filtre_tab}'"
            if poste:
                where_tab += f' AND poste_prescription="{poste.id}"'
                where_evo += f' AND poste_prescription="{poste.id}"'

            tab = api._requete("prescriptions", {
                "select": "annee, poste_prescription, libelle_poste_prescription, "
                          "montant_total_prescription_integer, montant_moyen_prescription_integer",
                "where": where_tab,
                "limit": 200,
            })
            evo = api._requete("prescriptions", {
                "select": "annee, montant_total_prescription_integer, montant_moyen_prescription_integer",
                "where": where_evo,
                "limit": 100,
            })
            return d, tab, evo

        # Requêtes parallèles (1 thread par département, max 10 simultanés)
        tous_tab, tous_evo = [], []
        with ThreadPoolExecutor(max_workers=min(10, len(depts_a_interroger))) as executor:
            futures = {executor.submit(_requete_dept, d): d for d in depts_a_interroger}
            for future in as_completed(futures):
                dept_obj, tab, evo = future.result()
                if tab:
                    for row in tab:
                        row["_dept_obj"] = dept_obj   # on attache le département à chaque ligne
                    tous_tab.extend(tab)
                if evo: tous_evo.extend(evo)

        if not tous_tab and not tous_evo:
            return render_template("erreur.html", type="api",
                message="L'API data.ameli.fr n'a pas répondu ou aucun résultat ne correspond."), 503

        # Agrégation des résultats tableau
        resultats = []
        for r in tous_tab:
            annee_brute = r.get("annee")
            annee_val   = int(annee_brute[:4]) if annee_brute else (annee or 0)
            dept_obj    = r.get("_dept_obj")
            resultats.append({
                "annee":            annee_val,
                "departement_code": dept_obj.code    if dept_obj else "",
                "departement_nom":  dept_obj.libelle if dept_obj else "",
                "poste":            r.get("libelle_poste_prescription") or "Inconnu",
                "nb_prescriptions": r.get("montant_moyen_prescription_integer") or 0,
                "montant_total":    r.get("montant_total_prescription_integer") or 0,
            })

        # Tri : Mode A → par année ; Mode B → par département
        if mode == "dept":
            resultats.sort(key=lambda x: x["annee"])
        else:
            resultats.sort(key=lambda x: (x["departement_code"], x["poste"]))

        # Agrégation de l'évolution (graphique)
        evolution_dict = {}
        for r in tous_evo:
            annee_brute = r.get("annee")
            annee_key   = int(annee_brute[:4]) if annee_brute else (annee or 0)
            if annee_key not in evolution_dict:
                evolution_dict[annee_key] = {"annee": annee_key, "nb_prescriptions": 0, "montant_total": 0.0}
            evolution_dict[annee_key]["nb_prescriptions"] += int(r.get("montant_moyen_prescription_integer") or 0)
            evolution_dict[annee_key]["montant_total"]    += float(r.get("montant_total_prescription_integer") or 0)

        evolution = sorted(evolution_dict.values(), key=lambda x: x["annee"])

        total_boites  = sum(int(r["nb_prescriptions"])  for r in resultats)
        total_montant = sum(float(r["montant_total"])    for r in resultats)

        return render_template("prescription.html",
                               regions=regions, professions=professions, postes=postes,
                               prof=prof, dept=dept, reg=reg,
                               depts_interroges=depts_a_interroger,
                               mode=mode,
                               annee=annee,
                               poste_id=poste_id, poste=poste,
                               resultats=resultats, evolution=evolution,
                               total_boites=total_boites, total_montant=total_montant)
    finally:
        session.close()


@bp_dashboard.route("/pathologies")
def pathologies():
    """Page de visualisation des pathologies."""
    return render_template("pathologies.html")


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
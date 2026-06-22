# controllers/auth.py
from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session as flask_session)

from models.db import Session # connexion à la base de données
from models.dimensions import Departement # modele de la tables des départements
from services.utilisateurs import (authentifier, chercher_par_identifiant,creer_utilisateur)
from services.grippe_api import GrippeAPI

bp_auth = Blueprint("auth", __name__)
grippe_api = GrippeAPI()


# ── Décorateur : exige une connexion ────────────────────────────────────────
def login_required(vue):
    """Redirige vers la connexion si aucun utilisateur n'est en session."""
    @wraps(vue)
    def wrapper(*args, **kwargs):
        if not flask_session.get("utilisateur"):
            return redirect(url_for("auth.connexion"))
        return vue(*args, **kwargs)
    return wrapper


# ── Connexion ────────────────────────────────────────────────────────────────
@bp_auth.route("/connexion", methods=["GET", "POST"])
def connexion():
    erreur = None
    if request.method == "POST":
        identifiant  = request.form.get("identifiant", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")

        bdd = Session()
        try:
            utilisateur = authentifier(bdd, identifiant, mot_de_passe)
            if utilisateur:
                flask_session["utilisateur"] = utilisateur.identifiant
                return redirect(url_for("auth.espace"))
        finally:
            bdd.close()

        erreur = "Identifiant ou mot de passe incorrect."

    return render_template("connexion.html", erreur=erreur)


# ── Création de compte ───────────────────────────────────────────────────────
@bp_auth.route("/creer-compte", methods=["GET", "POST"])
def creer_compte():
    erreur = None
    if request.method == "POST":
        identifiant  = request.form.get("identifiant", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")
        confirmation = request.form.get("confirmation", "")

        if not identifiant or not mot_de_passe:
            erreur = "Tous les champs sont obligatoires."
        elif mot_de_passe != confirmation:
            erreur = "Les deux mots de passe ne correspondent pas."
        else:
            bdd = Session()
            try:
                if chercher_par_identifiant(bdd, identifiant):
                    erreur = "Cet identifiant est déjà utilisé."
                else:
                    creer_utilisateur(bdd, identifiant, mot_de_passe)
                    flask_session["utilisateur"] = identifiant
                    return redirect(url_for("auth.espace"))
            finally:
                bdd.close()

    return render_template("creer_compte.html", erreur=erreur)


# ── Déconnexion ──────────────────────────────────────────────────────────────
@bp_auth.route("/deconnexion")
def deconnexion():
    flask_session.pop("utilisateur", None)
    return redirect("/")


# ── Page réservée aux utilisateurs connectés ─────────────────────────────────
@bp_auth.route("/espace")
@login_required
def espace():
    departement_id = request.args.get("departement_id", "").strip()
    classe_age      = request.args.get("classe_age", default="Tous âges", type=str)
    if classe_age not in GrippeAPI.CLASSES_AGE:
        classe_age = "Tous âges"

    bdd = Session()
    try:
        departements = bdd.query(Departement).order_by(Departement.code).all()
        dept = None
        if departement_id:
            dept = bdd.query(Departement).filter_by(code=departement_id).first()
    finally:
        bdd.close()

    # Courbe : évolution dans le temps (~6 saisons) pour le département choisi
    evolution = []
    if dept:
        evolution = grippe_api.get_evolution_departement(dept.code, classe_age)

    return render_template(
        "espace.html",
        departements=departements,
        departement_id=departement_id,
        dept=dept,
        classes_age=GrippeAPI.CLASSES_AGE,
        classe_age=classe_age,
        evolution=evolution,
    )
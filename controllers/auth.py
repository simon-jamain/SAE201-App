# controllers/auth.py

# ── Imports ──────────────────────────────────────────────────────────────────
from functools import wraps                          # permet de préserver les métadonnées de la fonction décorée (nom, docstring)
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session as flask_session)
# Blueprint      : permet de regrouper les routes liées à l'authentification dans un module indépendant
# render_template: charge et retourne un template Jinja2 (fichier HTML)
# request        : objet Flask donnant accès aux données de la requête HTTP (formulaire, paramètres URL)
# redirect       : redirige le navigateur vers une autre URL
# url_for        : génère dynamiquement l'URL d'une fonction de vue à partir de son nom
# flask_session  : dictionnaire côté serveur persistant entre les requêtes, utilisé pour retenir l'utilisateur connecté

from models.db import Session                        # fabrique de sessions SQLAlchemy pour accéder à la base de données
from models.dimensions import Departement            # modèle ORM de la table departement (utilisé dans la page espace)
from services.utilisateurs import (authentifier, chercher_par_identifiant, creer_utilisateur)
# authentifier          : vérifie identifiant + mot de passe et retourne l'objet Utilisateur ou None
# chercher_par_identifiant : recherche un compte existant par identifiant, retourne l'objet Utilisateur ou None
# creer_utilisateur     : crée un nouvel Utilisateur en base avec le mot de passe haché
from services.grippe_api import GrippeAPI            # classe d'accès à l'API Odissé (données grippales)

bp_auth = Blueprint("auth", __name__)                # déclare le Blueprint nommé "auth", rattaché à ce module
grippe_api = GrippeAPI()                             # instance unique de GrippeAPI partagée par toutes les requêtes de ce Blueprint


# ── Décorateur : exige une connexion ────────────────────────────────────────
def login_required(vue):
    """Redirige vers la connexion si aucun utilisateur n'est en session."""
    @wraps(vue)                                      # copie les métadonnées de la vue originale sur la fonction wrapper (nom, docstring)
    def wrapper(*args, **kwargs):
        if not flask_session.get("utilisateur"):     # vérifie si la clé "utilisateur" est présente dans la session Flask
            return redirect(url_for("auth.connexion"))  # si absente : redirige vers /connexion sans exécuter la vue
        return vue(*args, **kwargs)                  # si présente : exécute normalement la vue protégée
    return wrapper                                   # retourne la fonction wrapper qui remplace la vue originale


# ── Connexion ────────────────────────────────────────────────────────────────
@bp_auth.route("/connexion", methods=["GET", "POST"])  # accepte les méthodes GET (affichage) et POST (soumission du formulaire)
def connexion():
    """Affiche le formulaire de connexion et traite l'authentification."""
    erreur = None                                    # initialise la variable d'erreur à None (aucune erreur par défaut)
    if request.method == "POST":                     # si le formulaire a été soumis
        identifiant  = request.form.get("identifiant", "").strip()   # récupère l'identifiant saisi, supprime les espaces autour
        mot_de_passe = request.form.get("mot_de_passe", "")          # récupère le mot de passe saisi (sans strip : les espaces peuvent être volontaires)

        bdd = Session()                              # ouvre une session SQLAlchemy pour accéder à la base
        try:
            utilisateur = authentifier(bdd, identifiant, mot_de_passe)  # cherche le compte et vérifie le mot de passe haché
            if utilisateur:                          # si l'authentification réussit (objet Utilisateur retourné)
                flask_session["utilisateur"] = utilisateur.identifiant   # stocke l'identifiant dans la session Flask (marque l'utilisateur comme connecté)
                return redirect(url_for("auth.espace"))                  # redirige vers la page protégée /espace
        finally:
            bdd.close()                             # ferme la session SQLAlchemy dans tous les cas (succès ou exception)

        erreur = "Identifiant ou mot de passe incorrect."  # message d'erreur générique (ne précise pas lequel est faux, par sécurité)

    return render_template("connexion.html", erreur=erreur)  # en GET : affiche le formulaire vierge ; en POST échoué : réaffiche avec le message d'erreur


# ── Création de compte ───────────────────────────────────────────────────────
@bp_auth.route("/creer-compte", methods=["GET", "POST"])  # accepte GET (affichage) et POST (soumission)
def creer_compte():
    """Affiche le formulaire de création de compte et enregistre un utilisateur."""
    erreur = None                                    # initialise la variable d'erreur à None
    if request.method == "POST":                     # si le formulaire a été soumis
        identifiant  = request.form.get("identifiant", "").strip()   # récupère et nettoie l'identifiant
        mot_de_passe = request.form.get("mot_de_passe", "")          # récupère le mot de passe
        confirmation = request.form.get("confirmation", "")          # récupère la confirmation du mot de passe

        if not identifiant or not mot_de_passe:      # validation 1 : vérifie que les champs obligatoires ne sont pas vides
            erreur = "Tous les champs sont obligatoires."
        elif mot_de_passe != confirmation:           # validation 2 : vérifie que le mot de passe et sa confirmation sont identiques
            erreur = "Les deux mots de passe ne correspondent pas."
        else:                                        # les deux validations sont passées : on peut accéder à la base
            bdd = Session()                          # ouvre une session SQLAlchemy
            try:
                if chercher_par_identifiant(bdd, identifiant):         # vérifie qu'aucun compte n'existe déjà avec cet identifiant
                    erreur = "Cet identifiant est déjà utilisé."       # si doublon détecté : retourne une erreur sans créer le compte
                else:
                    creer_utilisateur(bdd, identifiant, mot_de_passe)  # crée le compte en base (hachage SHA-256 du mot de passe effectué dans le service)
                    flask_session["utilisateur"] = identifiant          # connecte immédiatement l'utilisateur sans qu'il ait à se reconnecter
                    return redirect(url_for("auth.espace"))             # redirige vers /espace
            finally:
                bdd.close()                         # ferme la session SQLAlchemy dans tous les cas

    return render_template("creer_compte.html", erreur=erreur)  # affiche le formulaire (vierge en GET, avec erreur en POST échoué)


# ── Déconnexion ──────────────────────────────────────────────────────────────
@bp_auth.route("/deconnexion")
def deconnexion():
    """Déconnecte l'utilisateur courant en supprimant la session Flask."""
    flask_session.pop("utilisateur", None)           # supprime la clé "utilisateur" de la session Flask (None évite une KeyError si absente)
    return redirect("/")                             # redirige vers la page d'accueil


# ── Page réservée aux utilisateurs connectés ─────────────────────────────────
@bp_auth.route("/espace")
@login_required                                      # applique le décorateur : redirige vers /connexion si aucun utilisateur en session
def espace():
    """Affiche l'espace privé avec les données grippales filtrées par département et tranche d'âge."""
    departement_id = request.args.get("departement_id", "").strip()              # récupère le code département depuis l'URL (paramètre optionnel)
    classe_age     = request.args.get("classe_age", default="Tous âges", type=str)  # récupère la classe d'âge depuis l'URL, "Tous âges" par défaut
    if classe_age not in GrippeAPI.CLASSES_AGE:      # vérifie que la classe d'âge reçue fait partie des valeurs autorisées
        classe_age = "Tous âges"                     # si valeur invalide ou absente : retombe sur la valeur par défaut

    bdd = Session()                                  # ouvre une session SQLAlchemy
    try:
        departements = bdd.query(Departement).order_by(Departement.code).all()   # récupère tous les départements triés par code (pour le formulaire de sélection)
        dept = None
        if departement_id:                           # si un département a été sélectionné par l'utilisateur
            dept = bdd.query(Departement).filter_by(code=departement_id).first() # récupère l'objet Departement correspondant au code saisi
    finally:
        bdd.close()                                  # ferme la session SQLAlchemy dans tous les cas

    # Courbe : évolution dans le temps (~6 saisons) pour le département choisi
    evolution = []                                   # initialise la liste des données grippales à vide
    if dept:                                         # n'appelle l'API que si un département valide a été trouvé en base
        evolution = grippe_api.get_evolution_departement(dept.code, classe_age)  # interroge l'API Odissé pour récupérer les données grippales du département et de la classe d'âge sélectionnés

    return render_template(
        "espace.html",
        departements=departements,   # liste de tous les départements pour remplir le formulaire de sélection
        departement_id=departement_id,  # code du département actuellement sélectionné (pour pré-remplir le select)
        dept=dept,                   # objet Departement sélectionné (ou None si aucun), utilisé pour afficher le nom dans la page
        classes_age=GrippeAPI.CLASSES_AGE,  # liste des tranches d'âge disponibles pour le second filtre
        classe_age=classe_age,       # tranche d'âge actuellement sélectionnée (pour pré-remplir le select)
        evolution=evolution,         # liste des enregistrements grippaux à afficher dans le graphique Chart.js
    )
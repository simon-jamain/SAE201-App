from flask import Blueprint, render_template, request, redirect, url_for

# Blueprint dédié au formulaire de contact
bp_contact = Blueprint("contact", __name__)

# Dictionnaire de correspondance clé → libellé pour les sujets du formulaire
# La clé est la valeur HTML du <select>, le libellé est affiché à l'utilisateur
SUJETS = {
    "bug":        "Signaler un bug",
    "donnees":    "Question sur les données",
    "suggestion": "Suggestion d'amélioration",
    "autre":      "Autre",
}

@bp_contact.route("/contact")
def index():
    """Affiche le formulaire de contact vide."""
    return render_template("contact.html")


@bp_contact.route("/contact/envoyer", methods=["POST"])
def envoyer():
    """
    Traite la soumission du formulaire de contact.
    - Valide que tous les champs sont remplis.
    - Affiche une page de confirmation en cas de succès.
    """
    # Récupération et nettoyage des champs du formulaire
    nom     = request.form.get("nom",     "").strip()
    email   = request.form.get("email",   "").strip()
    sujet   = request.form.get("sujet",   "").strip()
    message = request.form.get("message", "").strip()

    # Validation basique : tous les champs sont obligatoires
    if not all([nom, email, sujet, message]):
        return render_template("contact.html", erreur="Tous les champs sont obligatoires.")

    # Ici le message est simplement affiché en console.
    print(f"[Contact] De : {nom} <{email}> | Sujet : {sujet}\n{message}")

    # Affichage de la page de confirmation avec le libellé humain du sujet
    # SUJETS.get(sujet, sujet) : fallback sur la clé brute si le sujet est inconnu
    return render_template(
        "contact_confirmation.html",
        nom=nom,
        email=email,
        sujet_libelle=SUJETS.get(sujet, sujet),
        message=message,
    )
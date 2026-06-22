from flask import Blueprint, render_template, request, redirect, url_for

bp_contact = Blueprint("contact", __name__)

SUJETS = {
    "bug":        "Signaler un bug",
    "donnees":    "Question sur les données",
    "suggestion": "Suggestion d'amélioration",
    "autre":      "Autre",
}


@bp_contact.route("/contact")
def index():
    return render_template("contact.html")


@bp_contact.route("/contact/envoyer", methods=["POST"])
def envoyer():
    nom     = request.form.get("nom",     "").strip()
    email   = request.form.get("email",   "").strip()
    sujet   = request.form.get("sujet",   "").strip()
    message = request.form.get("message", "").strip()

    if not all([nom, email, sujet, message]):
        # Retour au formulaire avec un flag d'erreur
        return render_template("contact.html", erreur="Tous les champs sont obligatoires.")

    # TODO : brancher flask-mail pour un vrai envoi
    print(f"[Contact] De : {nom} <{email}> | Sujet : {sujet}\n{message}")

    return render_template(
        "contact_confirmation.html",
        nom=nom,
        email=email,
        sujet_libelle=SUJETS.get(sujet, sujet),
        message=message,
    )

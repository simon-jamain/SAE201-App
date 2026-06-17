# services/utilisateurs.py
import hashlib

from models.utilisateur import Utilisateur


# ── Fonction de hachage ──────────────────────────────────────────────────────
def hacher_mot_de_passe(mot_de_passe):
    """Hache un mot de passe avec SHA-256."""
    return hashlib.sha256(mot_de_passe.encode()).hexdigest()


# ── Fonction de comparaison de haché ─────────────────────────────────────────
def verifier_mot_de_passe(mot_de_passe, hache_stocke):
    """Compare le mot de passe saisi au haché stocké. True si identique."""
    return hacher_mot_de_passe(mot_de_passe) == hache_stocke


# ── Accès à la base ───────────────────────────────────────────────────────────
def chercher_par_identifiant(bdd, identifiant):
    """Renvoie l'utilisateur correspondant à l'identifiant, ou None."""
    return bdd.query(Utilisateur).filter_by(identifiant=identifiant).first()


def creer_utilisateur(bdd, identifiant, mot_de_passe):
    """Insère un nouvel utilisateur (id auto-incrémenté) et le renvoie."""
    utilisateur = Utilisateur(
        identifiant=identifiant,
        mot_de_passe_hache=hacher_mot_de_passe(mot_de_passe),
    )
    bdd.add(utilisateur)
    bdd.commit()
    return utilisateur


def authentifier(bdd, identifiant, mot_de_passe):
    """Cherche l'identifiant PUIS vérifie le mot de passe.

    Renvoie l'utilisateur si tout correspond, sinon None (identifiant inconnu
    OU mauvais mot de passe — message identique côté vue).
    """
    utilisateur = chercher_par_identifiant(bdd, identifiant)
    if utilisateur is None:
        return None
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hache):
        return None
    return utilisateur
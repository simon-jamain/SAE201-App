# services/utilisateurs.py
import hashlib  # module standard Python fournissant les algorithmes de hachage cryptographique (SHA-256, MD5, etc.)

from models.utilisateur import Utilisateur  # modèle ORM représentant la table utilisateur en base de données


# ── Fonction de hachage ──────────────────────────────────────────────────────
def hacher_mot_de_passe(mot_de_passe):
    """Hache un mot de passe avec SHA-256."""
    return hashlib.sha256(mot_de_passe.encode()).hexdigest()
    # .encode()    : convertit la chaîne de caractères en bytes (SHA-256 travaille sur des bytes, pas des str)
    # .sha256(...) : applique l'algorithme SHA-256, déterministe : le même mot de passe produit toujours le même haché
    # .hexdigest() : retourne le résultat sous forme de chaîne hexadécimale de 64 caractères


# ── Fonction de comparaison de haché ─────────────────────────────────────────
def verifier_mot_de_passe(mot_de_passe, hache_stocke):
    """Compare le mot de passe saisi au haché stocké. True si identique."""
    return hacher_mot_de_passe(mot_de_passe) == hache_stocke
    # recalcule le haché du mot de passe saisi et le compare au haché stocké en base
    # SHA-256 étant déterministe, deux mots de passe identiques produisent toujours le même haché
    # retourne True si les deux hachés sont identiques, False sinon


# ── Accès à la base ───────────────────────────────────────────────────────────
def chercher_par_identifiant(bdd, identifiant):
    """Renvoie l'utilisateur correspondant à l'identifiant, ou None."""
    return bdd.query(Utilisateur).filter_by(identifiant=identifiant).first()
    # .query(Utilisateur)          : sélectionne la table utilisateur via le modèle ORM
    # .filter_by(identifiant=...)  : filtre les enregistrements dont l'identifiant correspond exactement à la valeur reçue
    # .first()                     : retourne le premier résultat trouvé, ou None si aucun compte ne porte cet identifiant


def creer_utilisateur(bdd, identifiant, mot_de_passe):
    """Insère un nouvel utilisateur (id auto-incrémenté) et le renvoie."""
    utilisateur = Utilisateur(
        identifiant=identifiant,
        mot_de_passe_hache=hacher_mot_de_passe(mot_de_passe),  # le mot de passe est haché avant d'être stocké, il n'est jamais enregistré en clair
    )
    bdd.add(utilisateur)   # ajoute l'instance à la session SQLAlchemy (prépare l'insertion sans encore l'exécuter)
    bdd.commit()           # valide la transaction en base : l'id auto-incrémenté est généré par MySQL à cet instant
    return utilisateur     # retourne l'objet Utilisateur créé, avec son id désormais disponible


def authentifier(bdd, identifiant, mot_de_passe):
    """Cherche l'identifiant PUIS vérifie le mot de passe.

    Renvoie l'utilisateur si tout correspond, sinon None (identifiant inconnu
    OU mauvais mot de passe — message identique côté vue).
    """
    utilisateur = chercher_par_identifiant(bdd, identifiant)  # étape 1 : cherche un compte portant cet identifiant en base
    if utilisateur is None:
        return None  # identifiant inconnu : on retourne None sans vérifier le mot de passe
    if not verifier_mot_de_passe(mot_de_passe, utilisateur.mot_de_passe_hache):
        return None  # identifiant correct mais mot de passe erroné : on retourne None (même réponse que ci-dessus, par sécurité)
    return utilisateur  # les deux étapes ont réussi : retourne l'objet Utilisateur au contrôleur
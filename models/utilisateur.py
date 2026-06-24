# models/utilisateur.py
from sqlalchemy import Column, Integer, String  # types SQLAlchemy utilisés pour définir les colonnes de la table
# Column  : déclare une colonne de la table avec ses contraintes
# Integer : type entier, utilisé pour la clé primaire
# String  : type chaîne de caractères avec longueur maximale

from models.dimensions import Base  # on réutilise le même Base que les autres modèles
# Base est l'instance DeclarativeBase partagée par tous les modèles ORM du projet
# la réutiliser garantit que SQLAlchemy connaît toutes les tables lors de la création du schéma


class Utilisateur(Base):
    """Table des comptes : identifiant + mot de passe haché (sel inclus)."""
    __tablename__ = "utilisateur"  # nom de la table MySQL correspondante

    id                 = Column(Integer, primary_key=True, autoincrement=True)  # clé primaire entière, générée automatiquement par MySQL à chaque insertion
    identifiant        = Column(String(150), unique=True, nullable=False)        # identifiant de connexion, limité à 150 caractères, obligatoire et unique en base (doublon interdit)
    mot_de_passe_hache = Column(String(255), nullable=False)                     # empreinte SHA-256 du mot de passe, stockée sous forme hexadécimale (64 caractères), le mot de passe en clair n'est jamais enregistré
# models/utilisateur.py
from sqlalchemy import Column, Integer, String
from models.dimensions import Base  # on réutilise le même Base que les autres modèles


class Utilisateur(Base):
    """Table des comptes : identifiant + mot de passe haché (sel inclus)."""
    __tablename__ = "utilisateur"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    identifiant        = Column(String(150), unique=True, nullable=False)
    mot_de_passe_hache = Column(String(255), nullable=False)
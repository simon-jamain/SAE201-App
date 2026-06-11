from sqlalchemy import Column, Integer, String, Float, TypeDecorator
from sqlalchemy.orm import declarative_base
from datetime import date

Base = declarative_base()

# --- Convertisseur int → date -------------------------------------------
class IntAsDate(TypeDecorator):
    """
    Stocké en base comme un INT au format YYYYMMDD (ex : 20230415).
    Rendu en Python comme un objet datetime.date.
    """
    impl = Integer
    cache_ok = True

    def process_result_value(self, value, dialect):
        """À la lecture : int → date."""
        if value is None:
            return None
        try:
            return date(value // 10000,
                        (value % 10000) // 100,
                        value % 100)
        except (ValueError, TypeError):
            return None

    def process_bind_param(self, value, dialect):
        """À l'écriture : date → int."""
        if value is None:
            return None
        if isinstance(value, date):
            return value.year * 10000 + value.month * 100 + value.day
        return value  # déjà un int


# --- Modèles ORM -----------------------------------------------------------

class Region(Base):
    __tablename__ = "region"
    id      = Column(Integer, primary_key=True)
    code    = Column(String(10), unique=True)
    libelle = Column(String(100))

    def to_dict(self):
        return {"id": self.id, "code": self.code, "libelle": self.libelle}


class Departement(Base):
    __tablename__ = "departement"
    code      = Column(String(10), primary_key=True)
    libelle   = Column(String(100))
    region_id = Column(Integer)

    def to_dict(self):
        return {"code": self.code, "libelle": self.libelle,
                "region_id": self.region_id}


class ProfessionSante(Base):
    __tablename__ = "profession_sante"
    id      = Column(Integer, primary_key=True)
    libelle = Column(String(200))

    def to_dict(self):
        return {"id": self.id, "libelle": self.libelle}


class Specialite(Base):
    __tablename__ = "specialite"
    code             = Column(Integer, primary_key=True)
    libelle          = Column(String(100))
    code_profession  = Column(Integer)

    def to_dict(self):
        return {"code": self.code, "libelle": self.libelle,
                "code_profession": self.code_profession}


class ModeExercice(Base):
    __tablename__ = "mode_exercice"
    code    = Column(Integer, primary_key=True)
    libelle = Column(String(100))

    def to_dict(self):
        return {"code": self.code, "libelle": self.libelle}


class Categorie(Base):
    __tablename__ = "categorie"
    code    = Column(Integer, primary_key=True)
    libelle = Column(String(100))

    def to_dict(self):
        return {"code": self.code, "libelle": self.libelle}


class NiveauDiplome(Base):
    __tablename__ = "niveau_diplome"
    code    = Column(Integer, primary_key=True)
    libelle = Column(String(100))

    def to_dict(self):
        return {"code": self.code, "libelle": self.libelle}


class Annee(Base):
    """
    Table de dimension temporelle.
    La colonne `valeur` est stockée en INT mais représente une année.
    """
    __tablename__ = "annee"
    code   = Column(Integer, primary_key=True)
    valeur = Column(Integer)   # ex : 2021, 2022…

    def to_dict(self):
        return {"code": self.code, "valeur": self.valeur}


class Periode(Base):
    """
    Si les périodes sont stockées sous forme YYYYMMDD (int),
    IntAsDate les convertit automatiquement en date Python.
    Adapte les noms de colonnes à ton vrai schéma.
    """
    __tablename__ = "periode"
    code        = Column(Integer, primary_key=True)
    date_debut  = Column(IntAsDate)   # int en base → date en Python
    date_fin    = Column(IntAsDate)   # idem

    def to_dict(self):
        return {
            "code": self.code,
            "date_debut": self.date_debut.isoformat() if self.date_debut else None,
            "date_fin":   self.date_fin.isoformat()   if self.date_fin   else None,
        }
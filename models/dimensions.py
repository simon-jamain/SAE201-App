from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Region(Base):
    __tablename__ = "region"

    id      = Column(Integer, primary_key=True)
    code    = Column(String(10))
    libelle = Column(String(100))

    departements = relationship("Departement", back_populates="region")


class Departement(Base):
    __tablename__ = "departement"

    id        = Column(Integer, primary_key=True)
    code      = Column(String(10))
    libelle   = Column(String(100))
    region_id = Column(Integer, ForeignKey("region.id"))

    region = relationship("Region", back_populates="departements")


class ProfessionSante(Base):
    __tablename__ = "profession_sante"

    id      = Column(Integer, primary_key=True)
    libelle = Column(String(200))

class PostePrescription(Base):
    __tablename__ = "type_prescription"  # Vérifie que c'est bien le nom dans ta base de données

    id      = Column(Integer, primary_key=True)
    libelle = Column(String(200))
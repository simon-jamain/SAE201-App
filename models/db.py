from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config

# Un seul moteur pour toute l'application
engine = create_engine(Config.db_url(), pool_recycle=3600)

# Fabrique de sessions
Session = sessionmaker(bind=engine)
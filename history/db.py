"""Motor y fábrica de sesiones de SQLAlchemy para el historial de conversación."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from history.config import config
from history.models import Base

config.db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{config.db_path}", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

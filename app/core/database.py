"""Database setup — SQLAlchemy.

Default: local SQLite file (``zoya.db``), portable and zero-config.
Set ``DATABASE_URL`` to a PostgreSQL URL for production, e.g.
``postgresql+psycopg2://zoya:password@localhost:5432/zoya``.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (imports models so they register on Base)."""
    import app.models  # noqa: F401  (registers all models)

    Base.metadata.create_all(bind=engine)

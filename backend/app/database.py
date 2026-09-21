from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

class Base(DeclarativeBase):
    pass

settings = get_settings()
# Directories are created before the first connection; no database is shipped.
settings.initialize_directories()
engine = create_engine(f"sqlite:///{settings.root / 'data' / 'qhealth.sqlite3'}", connect_args={"check_same_thread": False, "timeout": 30})

@event.listens_for(engine, "connect")
def configure_sqlite(connection, _record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

@contextmanager
def session_scope():
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

def init_db():
    from .storage import entities  # Register all tables.
    Base.metadata.create_all(engine)

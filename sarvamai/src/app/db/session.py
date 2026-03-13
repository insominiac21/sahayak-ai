from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_engine = None
_session_factory = None
_init_lock = Lock()


def get_session_factory():
    """Create and cache SQLAlchemy engine/session factory for Postgres."""
    global _engine, _session_factory

    if _session_factory is not None:
        return _session_factory

    with _init_lock:
        if _session_factory is not None:
            return _session_factory

        _engine = create_engine(
            settings.POSTGRES_URL,
            pool_pre_ping=True,
            future=True,
        )
        _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        return _session_factory


def get_engine():
    get_session_factory()
    return _engine

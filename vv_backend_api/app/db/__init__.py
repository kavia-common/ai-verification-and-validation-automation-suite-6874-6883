"""
Database initialization and session management for the backend API.

This module configures SQLAlchemy using environment variables:
- DATABASE_URL: Optional. If provided, will be used for the DB connection (e.g., Postgres).
- DATA_DIR: Directory to store SQLite database file when DATABASE_URL is not provided.

Defaults to a local SQLite database at {DATA_DIR}/app.db if DATABASE_URL is not set.

Tables are auto-created on application startup via init_db(app).
"""
import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session, declarative_base

# GLOBALS
Base = declarative_base()
_engine = None  # type: ignore
_SessionFactory: Optional[scoped_session] = None


def _build_sqlite_url(data_dir: str) -> str:
    """Return a SQLite URL for a database file inside the given data directory."""
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "app.db")
    # sqlite URL format: sqlite:////absolute/path/to/db
    return f"sqlite:///{os.path.abspath(db_path)}"


def _get_database_url() -> str:
    """Read DATABASE_URL from env, otherwise build a SQLite URL using DATA_DIR."""
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.strip():
        return db_url.strip()
    data_dir = os.getenv("DATA_DIR", "./data")
    return _build_sqlite_url(data_dir)


def _engine_connect_args(db_url: str) -> dict:
    """
    Provide engine connect_args where needed (e.g., SQLite needs check_same_thread=False
    for multithreaded Flask dev server).
    """
    if db_url.startswith("sqlite:///"):
        return {"check_same_thread": False}
    return {}


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = _get_database_url()
        connect_args = _engine_connect_args(db_url)
        _engine = create_engine(db_url, echo=False, future=True, connect_args=connect_args)
    return _engine


def get_session_factory():
    """Get or create a scoped_session factory bound to the engine."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)
        _SessionFactory = scoped_session(factory)
    return _SessionFactory


# PUBLIC_INTERFACE
def get_db() -> Session:
    """
    Provide a thread-local SQLAlchemy Session.

    Callers should either use this as a context manager via session_scope(),
    or ensure they close the session when done (session.close()).
    """
    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Context manager for a transactional scope.

    Example:
        with session_scope() as db:
            db.add(obj)
    """
    session = get_db()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(app=None):
    """
    Initialize the database: import models and create tables if they don't exist.
    Call this during app startup.
    """
    # Import models to ensure they are registered with Base.metadata
    from . import models  # noqa: F401  # pylint: disable=unused-import

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    if app:
        # Optionally, you can tie teardown to app context
        @app.teardown_appcontext
        def remove_session(response_or_exc):
            """Remove the scoped session on app context teardown."""
            factory = get_session_factory()
            factory.remove()
            return response_or_exc

"""Database engine and session management.

- `engine` is the connection pool to the database.
- `SessionLocal` creates a new session (a unit of work) per request.
- `get_db` is a FastAPI dependency that opens a session and always closes it.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def build_engine(database_url: str, **kwargs) -> Engine:
    """Create an engine, applying SQLite-specific settings when needed."""
    is_sqlite = database_url.startswith("sqlite")
    # `timeout` makes SQLite wait for a lock instead of failing immediately.
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args, **kwargs)

    if is_sqlite:
        is_file_db = database_url not in ("sqlite://", "sqlite:///:memory:")

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            # SQLite does NOT enforce foreign keys unless this pragma is set on every connection.
            cursor.execute("PRAGMA foreign_keys=ON")
            if is_file_db:
                # WAL lets the API read while a background workflow writes.
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session and guarantee it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

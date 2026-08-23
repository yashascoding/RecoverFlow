"""Legacy sync session — use app.db.database for async operations."""
from app.db.database import Base, engine, get_db, async_session_factory  # noqa: F401

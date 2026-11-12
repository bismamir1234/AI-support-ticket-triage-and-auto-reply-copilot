from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite specific connect args for thread safety
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_sqlite_schema():
    """Create tables and apply lightweight additive column migrations for SQLite."""
    Base.metadata.create_all(bind=engine)
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    desired_columns = {
        "secondary_categories": "JSON DEFAULT '[]'",
        "needs_clarification": "BOOLEAN NOT NULL DEFAULT 0",
        "analysis_reason": "TEXT",
        "prompt_injection_detected": "BOOLEAN NOT NULL DEFAULT 0",
        "security_flags": "JSON DEFAULT '[]'",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(tickets)")).fetchall()
        existing_cols = {row[1] for row in rows}
        for col_name, col_def in desired_columns.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_def}"))


def get_db():
    """Dependency that provides an independent database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


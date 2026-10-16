"""Bounded PostgreSQL connection pool."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(database_url: str):
    if not database_url.startswith(
        "postgresql+psycopg://"
    ):
        raise ValueError("PostgreSQL required")

    engine = create_engine(
        database_url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return engine, factory

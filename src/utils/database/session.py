from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.enviroments import B2BEnvironments


class DatabaseSessionManager:
    """Gerencia sessões SQLAlchemy e o checkpointer SQLite do LangGraph."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.settings = B2BEnvironments()
        database_path = database_path or self.settings.ONBOARDING_DATABASE
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            URL.create("sqlite", database=str(database_path)),
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_pre_ping=True,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self._checkpointer_context = SqliteSaver.from_conn_string(
            database_path.as_posix()
        )
        self.checkpointer = self._checkpointer_context.__enter__()
        self.checkpointer.setup()
        self._closed = False

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        if self._closed:
            return
        self._checkpointer_context.__exit__(None, None, None)
        self.engine.dispose()
        self._closed = True


database_manager = DatabaseSessionManager()
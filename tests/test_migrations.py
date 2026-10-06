import pytest
from sqlalchemy import inspect, text

from src.services.database_initializer import initialize_onboarding_storage
from src.utils.database.session import DatabaseSessionManager
from src.utils.models import Base


def test_initial_migration_is_applied(database_manager):
    inspector = inspect(database_manager.engine)
    assert inspector.has_table("alembic_version")
    assert {
        "credit_bureau_rules",
        "risk_policies",
        "onboarding_requests",
    } <= set(inspector.get_table_names())

    with database_manager.engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    assert revision == "0001_initial_onboarding"


def test_existing_unversioned_schema_is_adopted(tmp_path):
    manager = DatabaseSessionManager(tmp_path / "legacy.sqlite3")
    try:
        Base.metadata.create_all(bind=manager.engine)

        initialize_onboarding_storage(manager)

        with manager.engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "0001_initial_onboarding"
    finally:
        manager.close()


def test_existing_schema_with_empty_version_table_is_adopted(tmp_path):
    manager = DatabaseSessionManager(tmp_path / "empty_version.sqlite3")
    try:
        Base.metadata.create_all(bind=manager.engine)
        with manager.engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )

        initialize_onboarding_storage(manager)

        with manager.engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "0001_initial_onboarding"
    finally:
        manager.close()


def test_partial_unversioned_schema_is_not_stamped(tmp_path):
    manager = DatabaseSessionManager(tmp_path / "partial.sqlite3")
    try:
        with manager.engine.begin() as connection:
            connection.execute(text("CREATE TABLE credit_bureau_rules (cnpj_suffix TEXT)"))

        with pytest.raises(RuntimeError, match="parte das tabelas"):
            initialize_onboarding_storage(manager)
    finally:
        manager.close()
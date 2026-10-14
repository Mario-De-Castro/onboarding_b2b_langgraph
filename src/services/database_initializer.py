from pathlib import Path
import logging

logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from src.utils.database.session import DatabaseSessionManager, database_manager
from src.utils.enviroments import B2BEnvironments
from src.utils.models import Base, CreditBureauRule, RiskPolicy
from src.utils.repository import CreditBureauRuleRepository, RiskPolicyRepository


DEFAULT_CREDIT_RULES = (
    {
        "cnpj_suffix": "0001",
        "risk_score": 15,
        "alerts": [],
        "justification": "Consulta simulada sem apontamentos relevantes.",
    },
    {
        "cnpj_suffix": "0002",
        "risk_score": 55,
        "alerts": ["Risco moderado: validar documentos e limites comerciais."],
        "justification": "A consulta simulada exige revisao manual antes da ativacao.",
    },
    {
        "cnpj_suffix": "0003",
        "risk_score": 90,
        "alerts": ["Risco alto: existem apontamentos relevantes no bureau simulado."],
        "justification": "A consulta simulada recomenda rejeitar o onboarding.",
    },
    {
        "cnpj_suffix": "DEFAULT",
        "risk_score": 55,
        "alerts": ["CNPJ sem regra de mock correspondente; revisao manual necessaria."],
        "justification": "Nao ha resultado configurado para este CNPJ no bureau simulado.",
    },
)

DEFAULT_RISK_POLICIES = (
    {"minimum_score": 0, "maximum_score": 39, "onboarding_status": "APPROVED"},
    {
        "minimum_score": 40,
        "maximum_score": 70,
        "onboarding_status": "MANUAL_REVIEW",
    },
    {"minimum_score": 71, "maximum_score": 100, "onboarding_status": "REJECTED"},
)


def _alembic_config(database_path: Path) -> Config:
    project_root = B2BEnvironments().PROJECT_ROOT
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.attributes["database_path"] = database_path
    config.set_main_option(
        "sqlalchemy.url",
        f"sqlite:///{database_path.as_posix()}".replace("%", "%%"),
    )
    return config


def _adopt_existing_schema(config: Config, database: DatabaseSessionManager) -> bool:
    inspector = inspect(database.engine)
    tables = set(inspector.get_table_names())
    managed_tables = set(Base.metadata.tables)
    existing_managed_tables = tables & managed_tables

    has_applied_revision = False
    if "alembic_version" in tables:
        with database.engine.connect() as connection:
            has_applied_revision = connection.execute(
                text("SELECT 1 FROM alembic_version LIMIT 1")
            ).first() is not None
    if has_applied_revision or not existing_managed_tables:
        return False
    if existing_managed_tables != managed_tables:
        raise RuntimeError(
            "Banco SQLite sem versão Alembic possui apenas parte das tabelas do app; "
            "faça backup e reconcilie o schema antes de migrar."
        )

    for table in Base.metadata.sorted_tables:
        existing_columns = {
            column["name"] for column in inspector.get_columns(table.name)
        }
        required_columns = {column.name for column in table.columns}
        if not required_columns <= existing_columns:
            raise RuntimeError(
                f"A tabela {table.name} não corresponde ao schema inicial Alembic."
            )

    command.stamp(config, "head")
    return True


def run_database_migrations(database: DatabaseSessionManager) -> None:
    config = _alembic_config(database.database_path)
    if not _adopt_existing_schema(config, database):
        command.upgrade(config, "head")


def initialize_onboarding_storage(
    database: DatabaseSessionManager | None = None,
) -> None:
    """
    Metodo responsavel por criar as tabelas do banco de dados e popular com regras de bureau e politicas de risco padrao.
    """
    database = database or database_manager
    run_database_migrations(database)

    with database.session_scope() as session:
        credit_repository = CreditBureauRuleRepository(session)
        for rule_data in DEFAULT_CREDIT_RULES:
            if credit_repository.get_by_suffix(rule_data["cnpj_suffix"]) is None:
                credit_repository.add(CreditBureauRule(**rule_data))

        risk_repository = RiskPolicyRepository(session)
        for policy_data in DEFAULT_RISK_POLICIES:
            if risk_repository.get_by_score(policy_data["minimum_score"]) is None:
                risk_repository.add(RiskPolicy(**policy_data))
        risk_repository.validate_complete_coverage()
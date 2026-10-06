from pathlib import Path

import pytest

from src.services.database_initializer import initialize_onboarding_storage
from src.utils.database.session import DatabaseSessionManager
from src.utils.schemas import FinancialExtraction


class FakeExtractor:
    def invoke(self, messages):
        return FinancialExtraction(
            faturamento_anual=1_250_000,
            dividas=150_000,
            num_socios=3,
            resumo_operacional="Extracao simulada para teste.",
        )


@pytest.fixture
def database_manager(tmp_path: Path):
    manager = DatabaseSessionManager(tmp_path / "test.sqlite3")
    initialize_onboarding_storage(manager)
    yield manager
    manager.close()


@pytest.fixture
def fake_extractor() -> FakeExtractor:
    return FakeExtractor()


@pytest.fixture
def onboarding_service(database_manager, fake_extractor, tmp_path: Path):
    from src.agents.onboarding_graph import OnboardingGraph
    from src.services.onboarding_application_service import OnboardingService

    compiled_graph = OnboardingGraph(
        structured_extractor=fake_extractor,
        database=database_manager,
    ).graph
    return OnboardingService(
        graph=compiled_graph,
        database=database_manager,
        files_dir=tmp_path / "uploads",
    )
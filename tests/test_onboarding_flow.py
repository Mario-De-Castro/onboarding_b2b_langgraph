from pathlib import Path

import pytest
from pydantic import ValidationError

from src.services.database_initializer import initialize_onboarding_storage
from src.services.onboarding_application_service import OnboardingService
from src.utils.database.session import DatabaseSessionManager
from src.utils.schemas.onboarding import OnboardingPostRequest


def make_request(cnpj: str = "12345678010002") -> OnboardingPostRequest:
    return OnboardingPostRequest(
        company_name="Acme Teste",
        cnpj=cnpj,
        document_text="Demonstracao financeira para teste.",
    )


def test_invalid_cnpj_is_rejected_by_input_schema():
    with pytest.raises(ValidationError, match="CNPJ deve conter 14 digitos"):
        make_request("123")


def test_moderate_risk_pauses_and_human_approval_resumes(
    onboarding_service: OnboardingService,
):
    result = onboarding_service.start(
        make_request(),
        b"Demonstracao financeira para teste.",
        "balance.txt",
    )

    assert result["compliance_score"] == 55
    assert result["onboarding_status"] == "MANUAL_REVIEW"
    assert result["paused_for_review"] is True

    final_result = onboarding_service.decide(result["onboarding_id"], "APPROVE")

    assert final_result["onboarding_status"] == "APPROVED"
    assert final_result["human_decision"] == "APPROVE"
    assert final_result["paused_for_review"] is False


def test_request_and_checkpoint_survive_manager_restart(
    tmp_path: Path,
    fake_extractor,
):
    from src.agents.onboarding_graph import OnboardingGraph

    database_path = tmp_path / "restart.sqlite3"
    files_dir = tmp_path / "restart_uploads"
    first_manager = DatabaseSessionManager(database_path)
    initialize_onboarding_storage(first_manager)
    first_graph = OnboardingGraph(
        structured_extractor=fake_extractor,
        database=first_manager,
    ).graph
    first_service = OnboardingService(
        graph=first_graph,
        database=first_manager,
        files_dir=files_dir,
    )

    pending = first_service.start(
        make_request(),
        b"Demonstracao financeira para teste.",
        "balance.txt",
    )
    onboarding_id = pending["onboarding_id"]
    assert pending["paused_for_review"] is True
    first_manager.close()

    second_manager = DatabaseSessionManager(database_path)
    try:
        initialize_onboarding_storage(second_manager)
        second_graph = OnboardingGraph(
            structured_extractor=fake_extractor,
            database=second_manager,
        ).graph
        second_service = OnboardingService(
            graph=second_graph,
            database=second_manager,
            files_dir=files_dir,
        )

        persisted = second_service.get_snapshot(onboarding_id)
        assert persisted["paused_for_review"] is True
        assert Path(files_dir / onboarding_id / "document.txt").is_file()

        final_result = second_service.decide(onboarding_id, "APPROVE")
        assert final_result["onboarding_status"] == "APPROVED"
        assert final_result["human_decision"] == "APPROVE"
    finally:
        second_manager.close()
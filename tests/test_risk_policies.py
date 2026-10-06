import pytest

from src.utils.models import RiskPolicy
from src.utils.repository import RiskPolicyRepository


@pytest.mark.parametrize(
    ("score", "expected_status"),
    [
        (39, "APPROVED"),
        (40, "MANUAL_REVIEW"),
        (70, "MANUAL_REVIEW"),
        (71, "REJECTED"),
    ],
)
def test_policy_score_boundaries(database_manager, score, expected_status):
    with database_manager.session_scope() as session:
        policy = RiskPolicyRepository(session).get_by_score(score)

    assert policy is not None
    assert policy.onboarding_status == expected_status


def test_rejects_overlapping_policy(database_manager):
    with database_manager.session_scope() as session:
        repository = RiskPolicyRepository(session)
        with pytest.raises(ValueError, match="sobrepoe"):
            repository.add(
                RiskPolicy(
                    minimum_score=39,
                    maximum_score=40,
                    onboarding_status="MANUAL_REVIEW",
                )
            )


def test_detects_policy_gap(database_manager):
    with database_manager.session_scope() as session:
        repository = RiskPolicyRepository(session)
        policy = repository.get_by_score(50)
        session.delete(policy)

    with database_manager.session_scope() as session:
        with pytest.raises(ValueError, match="lacuna"):
            RiskPolicyRepository(session).validate_complete_coverage()
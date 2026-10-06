from sqlalchemy import select
from sqlalchemy.orm import Session

from src.utils.models.risk_policy import RiskPolicy


class RiskPolicyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_score(self, score: int) -> RiskPolicy | None:
        statement = select(RiskPolicy).where(
            RiskPolicy.minimum_score <= score,
            RiskPolicy.maximum_score >= score,
        )
        matches = list(self.session.scalars(statement))
        if len(matches) > 1:
            raise ValueError(f"Mais de uma politica corresponde ao score {score}.")
        return matches[0] if matches else None

    def add(self, policy: RiskPolicy) -> RiskPolicy:
        self._validate_bounds(policy)
        overlap = self.session.scalar(
            select(RiskPolicy.id).where(
                RiskPolicy.minimum_score <= policy.maximum_score,
                RiskPolicy.maximum_score >= policy.minimum_score,
            )
        )
        if overlap is not None:
            raise ValueError(
                "A faixa da politica se sobrepoe a uma politica existente."
            )
        self.session.add(policy)
        self.session.flush()
        return policy

    def validate_complete_coverage(self) -> None:
        policies = list(
            self.session.scalars(
                select(RiskPolicy).order_by(RiskPolicy.minimum_score)
            )
        )
        if not policies:
            raise ValueError("Nenhuma politica de risco foi configurada.")

        expected_minimum = 0
        valid_statuses = {"APPROVED", "MANUAL_REVIEW", "REJECTED"}
        for policy in policies:
            self._validate_bounds(policy)
            if policy.onboarding_status not in valid_statuses:
                raise ValueError(
                    f"Status invalido na politica de risco: {policy.onboarding_status}."
                )
            if policy.minimum_score != expected_minimum:
                kind = "sobreposicao" if policy.minimum_score < expected_minimum else "lacuna"
                raise ValueError(f"Foi encontrada uma {kind} nas faixas de risco.")
            expected_minimum = policy.maximum_score + 1

        if expected_minimum != 101:
            raise ValueError("As faixas de risco devem cobrir todos os scores de 0 a 100.")

    @staticmethod
    def _validate_bounds(policy: RiskPolicy) -> None:
        if not (
            0 <= policy.minimum_score <= policy.maximum_score <= 100
        ):
            raise ValueError("A faixa de risco deve estar dentro do intervalo 0-100.")
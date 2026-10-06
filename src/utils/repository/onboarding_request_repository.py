from sqlalchemy import select
from sqlalchemy.orm import Session

from src.utils.models.onboarding_request import OnboardingRequest


class OnboardingRequestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, onboarding_id: str) -> OnboardingRequest | None:
        return self.session.get(OnboardingRequest, onboarding_id)

    def list_recent(self, limit: int = 100) -> list[OnboardingRequest]:
        statement = (
            select(OnboardingRequest)
            .order_by(OnboardingRequest.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add(self, request: OnboardingRequest) -> OnboardingRequest:
        self.session.add(request)
        self.session.flush()
        return request

    def update_result(
        self,
        onboarding_id: str,
        *,
        onboarding_status: str,
        compliance_score: int | None,
        compliance_flags: list[str],
        extracted_financials: dict | None,
        human_decision: str | None,
        paused_for_review: bool,
        error_message: str | None = None,
    ) -> OnboardingRequest:
        request = self.get_by_id(onboarding_id)
        if request is None:
            raise KeyError(onboarding_id)
        request.onboarding_status = onboarding_status
        request.compliance_score = compliance_score
        request.compliance_flags = compliance_flags
        request.extracted_financials = extracted_financials
        request.human_decision = human_decision
        request.paused_for_review = paused_for_review
        request.error_message = error_message
        self.session.flush()
        return request
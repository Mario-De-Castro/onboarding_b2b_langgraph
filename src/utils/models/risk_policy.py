from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.utils.models.base import Base


class RiskPolicy(Base):
    __tablename__ = "risk_policies"
    __table_args__ = (
        CheckConstraint(
            "minimum_score >= 0 AND maximum_score <= 100 "
            "AND minimum_score <= maximum_score",
            name="ck_risk_policy_score_range",
        ),
        UniqueConstraint("minimum_score", "maximum_score", name="uq_risk_policy_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    minimum_score: Mapped[int] = mapped_column(nullable=False)
    maximum_score: Mapped[int] = mapped_column(nullable=False)
    onboarding_status: Mapped[str] = mapped_column(String(32), nullable=False)
from sqlalchemy import CheckConstraint, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.utils.models.base import Base


class CreditBureauRule(Base):
    __tablename__ = "credit_bureau_rules"
    __table_args__ = (
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_credit_rule_score"),
    )

    cnpj_suffix: Mapped[str] = mapped_column(String(8), primary_key=True)
    risk_score: Mapped[int] = mapped_column(nullable=False)
    alerts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    justification: Mapped[str] = mapped_column(String(500), nullable=False)
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.utils.models.base import Base


class OnboardingRequest(Base):
    __tablename__ = "onboarding_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(14), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    onboarding_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )
    compliance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compliance_flags: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    extracted_financials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    paused_for_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
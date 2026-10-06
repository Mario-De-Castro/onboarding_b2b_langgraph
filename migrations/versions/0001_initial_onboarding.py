"""Create onboarding tables.

Revision ID: 0001_initial_onboarding
Revises:
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_onboarding"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_bureau_rules",
        sa.Column("cnpj_suffix", sa.String(length=8), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("alerts", sa.JSON(), nullable=False),
        sa.Column("justification", sa.String(length=500), nullable=False),
        sa.CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name="ck_credit_rule_score",
        ),
        sa.PrimaryKeyConstraint("cnpj_suffix"),
    )
    op.create_table(
        "risk_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("minimum_score", sa.Integer(), nullable=False),
        sa.Column("maximum_score", sa.Integer(), nullable=False),
        sa.Column("onboarding_status", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "minimum_score >= 0 AND maximum_score <= 100 "
            "AND minimum_score <= maximum_score",
            name="ck_risk_policy_score_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "minimum_score",
            "maximum_score",
            name="uq_risk_policy_range",
        ),
    )
    op.create_table(
        "onboarding_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_file_path", sa.String(length=1024), nullable=False),
        sa.Column("onboarding_status", sa.String(length=32), nullable=False),
        sa.Column("compliance_score", sa.Integer(), nullable=True),
        sa.Column("compliance_flags", sa.JSON(), nullable=False),
        sa.Column("extracted_financials", sa.JSON(), nullable=True),
        sa.Column("human_decision", sa.String(length=16), nullable=True),
        sa.Column("paused_for_review", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_onboarding_requests_cnpj",
        "onboarding_requests",
        ["cnpj"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_requests_cnpj", table_name="onboarding_requests")
    op.drop_table("onboarding_requests")
    op.drop_table("risk_policies")
    op.drop_table("credit_bureau_rules")
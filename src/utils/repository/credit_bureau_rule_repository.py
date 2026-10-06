from sqlalchemy import select
from sqlalchemy.orm import Session

from src.utils.models.credit_bureau_rule import CreditBureauRule
from src.utils.schemas import ComplianceAnalysis


class CreditBureauRuleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_suffix(self, cnpj_suffix: str) -> CreditBureauRule | None:
        return self.session.get(CreditBureauRule, cnpj_suffix)

    def get_for_cnpj(self, cnpj: str) -> ComplianceAnalysis:
        rule = self.get_by_suffix(cnpj[-4:]) or self.get_by_suffix("DEFAULT")
        if rule is None:
            raise LookupError("Nenhuma regra de bureau encontrada no banco de dados.")
        return ComplianceAnalysis(
            score_risco=rule.risk_score,
            alertas=rule.alerts,
            justificativa=rule.justification,
        )

    def add(self, rule: CreditBureauRule) -> CreditBureauRule:
        self.session.add(rule)
        self.session.flush()
        return rule
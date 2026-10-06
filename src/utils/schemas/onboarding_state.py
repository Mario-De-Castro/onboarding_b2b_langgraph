from typing import Annotated, Literal, TypedDict
from . import ExtractedFinancials
from langgraph.graph.message import add_messages


class OnboardingState(TypedDict):
    """
    Representa o estado do processo de onboarding de uma empresa, incluindo informações financeiras extraídas, 
    score de compliance, status do onboarding e decisões humanas.

    Atributos:
        company_name (str): Nome da empresa.
        cnpj (str): CNPJ da empresa.
        document_text (str): Texto do documento fornecido para análise.
        extracted_financials (ExtractedFinancials): Informações financeiras extraídas do documento.
        compliance_score (int): Score de compliance obtido a partir da análise do bureau.
        compliance_flags (list[str]): Lista de alertas de compliance identificados.
        onboarding_status (Literal["PENDING", "APPROVED", "REJECTED", "MANUAL_REVIEW"]): Status atual do processo de onboarding.
        human_decision (Literal["APPROVE", "REJECT"] | None): Decisão humana tomada durante a revisão manual, se aplicável.
        messages (Annotated[list, add_messages]): Lista de mensagens de log geradas durante o processo de onboarding, anotadas para serem adicionadas ao estado.
    """
    company_name: str
    cnpj: str
    document_text: str
    extracted_financials: ExtractedFinancials
    compliance_score: int
    compliance_flags: list[str]
    onboarding_status: Literal[
        "PENDING", "APPROVED", "REJECTED", "MANUAL_REVIEW"
    ]
    human_decision: Literal["APPROVE", "REJECT"] | None
    messages: Annotated[list, add_messages]
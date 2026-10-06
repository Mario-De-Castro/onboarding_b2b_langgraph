from pydantic import BaseModel

class FinancialExtraction(BaseModel):
    faturamento_anual: float | None = None
    dividas: float | None = None
    num_socios: int | None = None
    resumo_operacional: str = ""
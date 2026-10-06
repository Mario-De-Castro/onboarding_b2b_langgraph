from typing import TypedDict

class ExtractedFinancials(TypedDict):
    faturamento_anual: float | None
    dividas: float | None
    num_socios: int | None
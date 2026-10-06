from pydantic import BaseModel, Field

class ComplianceAnalysis(BaseModel):
    score_risco: int = Field(ge=0, le=100)
    alertas: list[str]
    justificativa: str
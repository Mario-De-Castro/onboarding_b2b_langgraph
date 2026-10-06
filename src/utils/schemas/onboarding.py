from pydantic import BaseModel, Field, field_validator
import re
from src.utils.enviroments import B2BEnvironments

class OnboardingPostRequest(BaseModel):
    company_name: str = Field(..., min_length=1)
    cnpj: str
    document_text: str = Field(..., min_length=1)

    @field_validator("company_name", mode="before")
    def validate_company_name(cls, company_name: str) -> str:
        if not company_name.strip():
            raise ValueError("O nome da empresa nao pode estar vazio.")
        return company_name.strip()

    @field_validator("cnpj", mode="before")
    def normalize_cnpj(cls, cnpj: str) -> str:
        digits = re.sub(r"\D", "", cnpj)
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 digitos.")
        return digits

    @field_validator("document_text", mode="before")
    def validate_document_text(cls, document_text: str) -> str:
        document_text = document_text.strip()
        if not document_text:
            raise ValueError("O documento de texto esta vazio.")
        return document_text

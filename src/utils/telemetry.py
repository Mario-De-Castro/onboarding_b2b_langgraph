from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator, Literal
import ssl
import httpx

from src.utils.enviroments import B2BEnvironments

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationScore:
    name: str
    value: float | bool
    data_type: Literal["NUMERIC", "BOOLEAN"]
    comment: str

@dataclass
class WorkflowTrace:
    client: Any
    span: Any

    def update(self, **attributes: Any) -> None:
        self.span.update(**attributes)

def _langfuse_client():
    """
    Cria e retorna uma instância do cliente Langfuse, se a telemetria estiver habilitada e as chaves de API estiverem configuradas,
    Retorna None se a telemetria estiver desabilitada ou se houver algum erro ao inicializar o cliente.
    Returns:
        Any | None: Instância do cliente Langfuse ou None se a telemetria estiver desabilitada.
    """
    settings = B2BEnvironments()
    if not (
        settings.LANGFUSE_TRACING_ENABLED
        and settings.LANGFUSE_PUBLIC_KEY
        and settings.LANGFUSE_SECRET_KEY
    ):
        return None

    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            base_url=settings.LANGFUSE_BASE_URL,
            tracing_enabled=settings.LANGFUSE_TRACING_ENABLED,
        )
    except Exception:
        logger.exception("Nao foi possivel inicializar o cliente Langfuse.")
        return None

@contextmanager
def observe_operation(
    name: str,
    *,
    as_type: str = "span",
    input: dict | None = None,
    model: str | None = None,
) -> Iterator[Any]:
    """
    Observa uma operação e registra métricas de telemetria.
    Args:
        name (str): Nome da operação.
        as_type (str): Tipo de observação.
        input (dict | None): Dados de entrada.
        model (str | None): Modelo associado à operação.
    Returns:
        Iterator[Any]: Iterador que fornece a observação.
    """
    client = _langfuse_client()
    if client is None:
        yield None
        return

    options = {"name": name, "as_type": as_type, "input": input}
    if model is not None:
        options["model"] = model
    with client.start_as_current_observation(**options) as span:
        yield span

@contextmanager
def trace_workflow(onboarding_id: str, execution: str) -> Iterator[WorkflowTrace | None]:
    """
    Rastreia um fluxo de trabalho e registra métricas de telemetria.
    Args:
        onboarding_id (str): ID do onboarding.
        execution (str): Execução do fluxo.
    Returns:
        Iterator[WorkflowTrace | None]: Iterador que fornece o rastreamento do workflow.
    """
    client = _langfuse_client()
    if client is None:
        yield None
        return

    from langfuse import Langfuse, propagate_attributes

    trace_id = Langfuse.create_trace_id(seed=f"{onboarding_id}:{execution}")
    settings = B2BEnvironments()
    with client.start_as_current_observation(
        name="b2b_onboarding",
        as_type="span",
        trace_context={"trace_id": trace_id},
        input={"execution": execution},
        metadata={"workflow": "b2b_onboarding"},
    ) as span:
        with propagate_attributes(
            session_id=onboarding_id,
            trace_name="B2B onboarding",
            environment=settings.LANGFUSE_TRACING_ENVIRONMENT,
            tags=["onboarding", execution],
        ):
            yield WorkflowTrace(client=client, span=span)

def record_evaluation_scores(
    trace: WorkflowTrace | None,
    scores: list[EvaluationScore],
) -> None:
    """
    Registra ppontuações de avaliação no Langfuse.
    Args:
        trace (WorkflowTrace | None): Rastreamento do workflow.
        scores (list[EvaluationScore]): Lista de pontuações de avaliação.
    """
    if trace is None:
        return

    try:
        trace_id = trace.client.get_current_trace_id()
        if trace_id is None:
            return
        for score in scores:
            trace.client.create_score(
                trace_id=trace_id,
                name=score.name,
                value=float(score.value) if score.data_type == "BOOLEAN" else score.value,
                data_type=score.data_type,
                comment=score.comment,
            )
    except Exception:
        logger.exception("Nao foi possivel registrar as avaliacoes no Langfuse.")

def _parse_document_number(value: str) -> Decimal | None:
    """
    Analisa um número de documento e retorna um Decimal normalizado.
    Args:
        value (str): Valor do número de documento.
    Returns:
        Decimal | None: Número de documento normalizado ou None se inválido.
    """
    normalized = value.strip().rstrip(".,")
    if not normalized:
        return None

    if "," in normalized and "." in normalized:
        decimal_separator = "," if normalized.rfind(",") > normalized.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(grouping_separator, "")
        normalized = normalized.replace(decimal_separator, ".")
    elif "," in normalized or "." in normalized:
        separator = "," if "," in normalized else "."
        parts = normalized.split(separator)
        if len(parts) > 2 or (len(parts[-1]) == 3 and len(parts[0]) <= 3):
            normalized = "".join(parts)
        else:
            normalized = normalized.replace(separator, ".")

    try:
        return Decimal(normalized).normalize()
    except InvalidOperation:
        return None

def evaluate_financial_extraction(
    document_text: str,
    extracted_financials: dict[str, Any],
) -> list[EvaluationScore]:
    """
    Avalia a extração de informações financeiras.
    Args:
        document_text (str): Texto do documento.
        extracted_financials (dict[str, Any]): Informações financeiras extraídas.
    Returns:
        list[EvaluationScore]: Lista de pontuações de avaliação.
    """
    fields = ("faturamento_anual", "dividas", "num_socios")
    schema_valid = all(
        field in extracted_financials
        and (
            extracted_financials[field] is None
            or (
                isinstance(extracted_financials[field], (int, float))
                and not isinstance(extracted_financials[field], bool)
            )
        )
        for field in fields
    )

    source_numbers = {
        number
        for token in re.findall(r"(?<!\w)-?\d[\d.,]*", document_text)
        if (number := _parse_document_number(token)) is not None
    }
    claims = [extracted_financials.get(field) for field in fields]
    claims = [
        claim
        for claim in claims
        if isinstance(claim, (int, float)) and not isinstance(claim, bool)
    ]
    supported_claims = sum(
        Decimal(str(claim)).normalize() in source_numbers for claim in claims
    )
    grounding = supported_claims / len(claims) if claims else 1.0

    return [
        EvaluationScore(
            name="financial_extraction_schema_valid",
            value=schema_valid,
            data_type="BOOLEAN",
            comment=(
                "Os campos financeiros esperados possuem valores numericos ou null."
                if schema_valid
                else "A extracao nao corresponde ao schema financeiro esperado."
            ),
        ),
        EvaluationScore(
            name="financial_numeric_grounding",
            value=grounding,
            data_type="NUMERIC",
            comment=(
                f"{supported_claims} de {len(claims)} valores numericos extraidos "
                "foram encontrados no documento."
                if claims
                else "Nenhum valor numerico foi extraido para verificacao."
            ),
        ),
    ]
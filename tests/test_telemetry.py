from unittest.mock import Mock

from src.utils.telemetry import (
    WorkflowTrace,
    _langfuse_client,
    evaluate_financial_extraction,
)


def test_langfuse_client_receives_configured_credentials(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://langfuse.example/")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    constructor = Mock(return_value=object())
    monkeypatch.setattr("langfuse.Langfuse", constructor)

    _langfuse_client()

    constructor.assert_called_once_with(
        public_key="pk-test",
        secret_key="sk-test",
        base_url="https://langfuse.example",
        tracing_enabled=True,
    )


def test_workflow_trace_updates_root_span():
    span = Mock()

    WorkflowTrace(client=Mock(), span=span).update(output={"status": "APPROVED"})

    span.update.assert_called_once_with(output={"status": "APPROVED"})


def test_evaluation_recognizes_brazilian_financial_number_formats():
    scores = evaluate_financial_extraction(
        "Receita anual de R$ 1.250.000,00 e dívidas de R$ 150.000,00.",
        {
            "faturamento_anual": 1_250_000,
            "dividas": 150_000,
            "num_socios": None,
        },
    )

    assert scores[0].value is True
    assert scores[1].value == 1.0


def test_evaluation_reports_ungrounded_values_and_invalid_schema():
    scores = evaluate_financial_extraction(
        "Receita anual de R$ 1.250.000,00.",
        {
            "faturamento_anual": 1_250_000,
            "dividas": "150 mil",
            "num_socios": True,
        },
    )

    assert scores[0].value is False
    assert scores[1].value == 1.0


def test_evaluation_does_not_penalize_fields_without_numeric_claims():
    scores = evaluate_financial_extraction(
        "O documento não informa valores financeiros.",
        {
            "faturamento_anual": None,
            "dividas": None,
            "num_socios": None,
        },
    )

    assert scores[1].value == 1.0
    assert "Nenhum valor numerico" in scores[1].comment
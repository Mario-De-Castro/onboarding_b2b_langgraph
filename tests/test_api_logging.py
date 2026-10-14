import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import request_logging_middleware
from src.utils.logger.logging import get_logger


def test_get_logger_applies_configured_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    assert get_logger("test.configured_level").level == logging.INFO


def test_request_middleware_logs_response_statuses(caplog):
    app = FastAPI()
    app.middleware("http")(request_logging_middleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/created", status_code=201)
    def create_resource():
        return {"status": "created"}

    caplog.set_level(logging.INFO, logger="src.api")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/created").status_code == 201

    assert "HTTP GET /health -> 200" in caplog.text
    assert "HTTP POST /created -> 201" in caplog.text
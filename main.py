"""Ponto de entrada para executar a API de onboarding."""

import uvicorn

from src.api import app
from src.utils.enviroments import B2BEnvironments


if __name__ == "__main__":
    settings = B2BEnvironments()
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
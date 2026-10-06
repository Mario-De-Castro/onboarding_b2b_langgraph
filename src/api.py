"""Composição da aplicação FastAPI e registro das rotas HTTP."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.route.onboarding import router as onboarding_router
from src.services.database_initializer import initialize_onboarding_storage
from src.utils.database.session import database_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
	initialize_onboarding_storage()
	try:
		yield
	finally:
		database_manager.close()


app = FastAPI(
	title="B2B Onboarding Agent",
	version="1.0.0",
	lifespan=lifespan,
)
app.include_router(onboarding_router)
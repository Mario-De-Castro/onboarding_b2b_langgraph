"""Composição da aplicação FastAPI e registro das rotas HTTP."""

from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from starlette.responses import Response

from src.route.onboarding import router as onboarding_router
from src.services.database_initializer import initialize_onboarding_storage
from src.utils.database.session import database_manager
from src.utils.logger.logging import get_logger

logger = get_logger(__name__)


async def request_logging_middleware(request: Request, call_next) -> Response:
	started_at = perf_counter()
	try:
		response = await call_next(request)
	except Exception:
		route = request.scope.get("route")
		path = getattr(route, "path", request.url.path)
		logger.exception(
			"HTTP %s %s failed after %.2f ms",
			request.method,
			path,
			(perf_counter() - started_at) * 1000,
		)
		raise

	route = request.scope.get("route")
	path = getattr(route, "path", request.url.path)
	logger.info(
		"HTTP %s %s -> %d (%.2f ms)",
		request.method,
		path,
		response.status_code,
		(perf_counter() - started_at) * 1000,
	)
	return response


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
app.middleware("http")(request_logging_middleware)
app.include_router(onboarding_router)
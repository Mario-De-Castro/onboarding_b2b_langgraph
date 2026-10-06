"""API HTTP para iniciar e revisar processos de onboarding B2B."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from src.services.onboarding_application_service import OnboardingService
from src.utils.enviroments import B2BEnvironments
from src.utils.logger.logging import get_logger

from src.utils.schemas.human_decision import HumanDecisionRequest
from src.utils.schemas.onboarding import OnboardingPostRequest


settings = B2BEnvironments()
logger = get_logger(__name__)
onboarding_service = OnboardingService()
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/onboardings", status_code=202)
async def create_onboarding(
    company_name: str = Form(...),
    cnpj: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    file_content = await file.read(settings.MAX_FILE_SIZE_BYTES + 1)
    if len(file_content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o tamanho permitido.")
    try:
        document_text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=415,
            detail="Envie um arquivo de texto codificado em UTF-8.",
        ) from exc

    try:
        request = OnboardingPostRequest(
            company_name=company_name,
            cnpj=cnpj,
            document_text=document_text,
        )
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise HTTPException(status_code=422, detail=errors) from exc

    try:
        result = await run_in_threadpool(
            onboarding_service.start,
            request,
            file_content,
            file.filename or "document.txt",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao executar onboarding")
        raise HTTPException(
            status_code=502,
            detail="Falha ao processar o documento. Verifique o Ollama e o modelo configurado.",
        ) from exc
    return result

@router.get("/onboardings/{onboarding_id}")
async def get_onboarding(onboarding_id: str) -> dict:
    try:
        return await run_in_threadpool(
            onboarding_service.get_snapshot,
            onboarding_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Onboarding nao encontrado.") from exc


@router.post("/onboardings/{onboarding_id}/decision")
async def submit_human_decision(
    onboarding_id: str,
    request: HumanDecisionRequest,
) -> dict:
    try:
        snapshot = await run_in_threadpool(
            onboarding_service.decide,
            onboarding_id,
            request.decision,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Onboarding nao encontrado.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao retomar onboarding %s", onboarding_id)
        raise HTTPException(
            status_code=502,
            detail="Falha ao retomar o onboarding.",
        ) from exc
    return snapshot
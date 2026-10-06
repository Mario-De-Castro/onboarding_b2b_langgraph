from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Literal

from langgraph.graph.state import CompiledStateGraph

from src.agents.onboarding_graph import OnboardingGraph
from src.utils.database.session import DatabaseSessionManager, database_manager
from src.utils.enviroments import B2BEnvironments
from src.utils.models import OnboardingRequest
from src.utils.repository import OnboardingRequestRepository
from src.utils.schemas import OnboardingState
from src.utils.schemas.onboarding import OnboardingPostRequest
from src.utils.logger.logging import get_logger

logger = get_logger(__name__)

class OnboardingService:
    """Coordena persistência local, regras e execução do grafo de onboarding."""

    def __init__(
        self,
        graph: CompiledStateGraph | None = None,
        *,
        database: DatabaseSessionManager | None = None,
        files_dir: Path | None = None,
    ) -> None:
        self.settings = B2BEnvironments()
        self.database = database or database_manager
        self.files_dir = files_dir or self.settings.ONBOARDING_FILES_DIR
        self.graph = graph or OnboardingGraph(database=self.database).graph

    @staticmethod
    def _config(onboarding_id: str) -> dict:
        """
        Configura o grafo de onboarding com o ID do onboarding.
        Args:
            onboarding_id (str): ID do onboarding.
        Returns:
            dict: Configuração do grafo.
        """
        return {"configurable": {"thread_id": onboarding_id}}

    @staticmethod
    def _serialize_request(request: OnboardingRequest) -> dict:
        """
        Serializa a requisição de onboarding em um dicionário.
        Args:
            request (OnboardingRequest): Requisição de onboarding.
        Returns:
            dict: Dicionário com os dados serializados.
        """
        return {
            "onboarding_id": request.id,
            "company_name": request.company_name,
            "cnpj": request.cnpj,
            "original_filename": request.original_filename,
            "stored_file_path": os.path.basename(request.stored_file_path),
            "extracted_financials": request.extracted_financials,
            "compliance_score": request.compliance_score,
            "compliance_flags": request.compliance_flags,
            "onboarding_status": request.onboarding_status,
            "human_decision": request.human_decision,
            "paused_for_review": request.paused_for_review,
            "error_message": request.error_message,
            "created_at": request.created_at.isoformat(),
            "updated_at": request.updated_at.isoformat(),
        }

    @staticmethod
    def _initial_state(
        company_name: str,
        cnpj: str,
        document_text: str,
    ) -> OnboardingState:
        """
        Inicializa o estado do onboarding.
        Args:
            company_name (str): Nome da empresa.
            cnpj (str): CNPJ da empresa.
            document_text (str): Texto do documento.
        Returns:
            OnboardingState: Estado inicial do onboarding.
        """
        return {
            "company_name": company_name,
            "cnpj": cnpj,
            "document_text": document_text,
            "extracted_financials": {
                "faturamento_anual": None,
                "dividas": None,
                "num_socios": None,
            },
            "compliance_score": 0,
            "compliance_flags": [],
            "onboarding_status": "PENDING",
            "human_decision": None,
            "messages": [],
        }

    def _store_document(
        self,
        onboarding_id: str,
        original_filename: str,
        file_content: bytes,
    ) -> Path:
        """
        Armazena o documento no sistema de arquivos.

        Args:
            onboarding_id (str): ID do onboarding.
            original_filename (str): Nome original do arquivo.
            file_content (bytes): Conteúdo do arquivo.
        
        Returns:
            Path: Caminho do arquivo armazenado.
        """
        extension = Path(original_filename.replace("\\", "/")).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
            extension = ".txt"

        request_directory = self.files_dir / onboarding_id
        request_directory.mkdir(parents=True, exist_ok=False)
        stored_path = request_directory / f"document{extension}"
        stored_path.write_bytes(file_content)
        return stored_path.resolve()

    def _update_from_graph(self, onboarding_id: str, snapshot) -> None:
        """
        Atualiza o estado do onboarding no banco de dados com base no snapshot do grafo.
        Args:
            onboarding_id (str): ID do onboarding.
            snapshot: Snapshot do grafo de onboarding.
        Raises:
            RuntimeError: Se o snapshot não contiver valores.
        """
        values = snapshot.values
        if not values:
            raise RuntimeError("O grafo nao retornou estado para o onboarding.")

        with self.database.session_scope() as session:
            OnboardingRequestRepository(session).update_result(
                onboarding_id,
                onboarding_status=values["onboarding_status"],
                compliance_score=values["compliance_score"],
                compliance_flags=values["compliance_flags"],
                extracted_financials=values["extracted_financials"],
                human_decision=values["human_decision"],
                paused_for_review="human_review_node" in snapshot.next,
            )

    def start(
        self,
        request: OnboardingPostRequest,
        file_content: bytes,
        original_filename: str,
    ) -> dict:
        """
        Inicia o processo de onboarding, armazenando o documento e executando o grafo de onboarding.
        Args:
            request (OnboardingPostRequest): Requisição de onboarding.
            file_content (bytes): Conteúdo do arquivo enviado.
            original_filename (str): Nome original do arquivo enviado.
        Returns:
            dict: Snapshot final do onboarding.
        """
        company_name = request.company_name
        cnpj = request.cnpj
        document_text = request.document_text
        onboarding_id = str(uuid.uuid4())
        safe_original_filename = Path(
            (original_filename or "document.txt").replace("\\", "/")
        ).name[:255]
        stored_path = self._store_document(
            onboarding_id,
            safe_original_filename,
            file_content,
        )

        try:
            with self.database.session_scope() as session:
                OnboardingRequestRepository(session).add(
                    OnboardingRequest(
                        id=onboarding_id,
                        company_name=company_name,
                        cnpj=cnpj,
                        original_filename=safe_original_filename,
                        stored_file_path=str(stored_path),
                    )
                )
        except Exception:
            stored_path.unlink(missing_ok=True)
            stored_path.parent.rmdir()
            raise

        try:
            config = self._config(onboarding_id)
            for _ in self.graph.stream(
                self._initial_state(company_name, cnpj, document_text),
                config,
                stream_mode="updates",
            ):
                pass
            self._update_from_graph(onboarding_id, self.graph.get_state(config))
        except Exception as exc:
            with self.database.session_scope() as session:
                OnboardingRequestRepository(session).update_result(
                    onboarding_id,
                    onboarding_status="FAILED",
                    compliance_score=None,
                    compliance_flags=[],
                    extracted_financials=None,
                    human_decision=None,
                    paused_for_review=False,
                    error_message=str(exc),
                )
            raise

        return self.get_snapshot(onboarding_id)

    def get_snapshot(self, onboarding_id: str) -> dict:
        """
        Recupera o snapshot do onboarding a partir do banco de dados.
        Args:
            onboarding_id (str): ID do onboarding.
        Returns:
            dict: Snapshot do onboarding.
        """
        with self.database.session_scope() as session:
            request = OnboardingRequestRepository(session).get_by_id(onboarding_id)
            if request is None:
                raise KeyError(onboarding_id)
            return self._serialize_request(request)

    def decide(
        self,
        onboarding_id: str,
        decision: Literal["APPROVE", "REJECT"],
    ) -> dict:
        """
        Submete a decisão humana para o onboarding, atualizando o estado do grafo e o banco de dados.
        Args:
            onboarding_id (str): ID do onboarding.
            decision (Literal["APPROVE", "REJECT"]): Decisão humana.
        Returns:
            dict: Snapshot final do onboarding.
        """
        with self.database.session_scope() as session:
            request = OnboardingRequestRepository(session).get_by_id(onboarding_id)
            if request is None:
                raise KeyError(onboarding_id)
            if not request.paused_for_review:
                raise ValueError("Este onboarding nao esta aguardando revisao humana.")

        config = self._config(onboarding_id)
        snapshot = self.graph.get_state(config)
        if "human_review_node" not in snapshot.next:
            raise ValueError("O estado do grafo nao esta aguardando revisao humana.")

        self.graph.update_state(config, {"human_decision": decision})
        for _ in self.graph.stream(None, config, stream_mode="updates"):
            pass
        self._update_from_graph(onboarding_id, self.graph.get_state(config))
        return self.get_snapshot(onboarding_id)
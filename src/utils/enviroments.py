
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")



class B2BEnvironments:
    """Centraliza a configuração da API e do Ollama."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def HOST(self) -> str:
        return os.getenv("HOST", "127.0.0.1")

    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", "8000"))

    @property
    def OLLAMA_URL(self) -> str:
        return os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

    @property
    def OLLAMA_MODEL(self) -> str:
        return os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    @property
    def OLLAMA_EMBEDDING_MODEL(self) -> str:
        return os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    @property
    def OLLAMA_TIMEOUT(self) -> float:
        return float(os.getenv("OLLAMA_TIMEOUT", "180"))

    @property
    def LANGFUSE_PUBLIC_KEY(self) -> str:
        return os.getenv("LANGFUSE_PUBLIC_KEY", "")

    @property
    def LANGFUSE_SECRET_KEY(self) -> str:
        return os.getenv("LANGFUSE_SECRET_KEY", "")

    @property
    def LANGFUSE_BASE_URL(self) -> str:
        return os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com").rstrip("/")

    @property
    def LANGFUSE_TRACING_ENVIRONMENT(self) -> str:
        return os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development")

    @property
    def LANGFUSE_TRACING_ENABLED(self) -> bool:
        return os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() in {
            "1", "true", "yes", "on"
        }

    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def PROJECT_ROOT(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return int(os.getenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))

    @property
    def ONBOARDING_DATABASE(self) -> Path:
        return Path(
            os.getenv(
                "ONBOARDING_DATABASE",
                str(self.PROJECT_ROOT / "data" / "onboarding.sqlite3"),
            )
        )

    @property
    def ONBOARDING_FILES_DIR(self) -> Path:
        return Path(
            os.getenv(
                "ONBOARDING_FILES_DIR",
                str(self.PROJECT_ROOT / "data" / "onboarding_files"),
            )
        )

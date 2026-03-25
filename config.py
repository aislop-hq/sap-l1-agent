"""Configuration — loads all env vars with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-ada-002", alias="OPENAI_EMBEDDING_MODEL")

    # Langfuse
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", alias="LANGFUSE_HOST"
    )

    # Qdrant
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="sap_runbooks", alias="QDRANT_COLLECTION")

    # SSH
    ssh_default_user: str = Field(default="sapsidadm", alias="SSH_DEFAULT_USER")
    ssh_key_path: str = Field(default="~/.ssh/id_rsa", alias="SSH_KEY_PATH")
    ssh_port: int = Field(default=22, alias="SSH_PORT")

    # Demo mode — full demo (no external deps), overrides mock_ssh
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    # Mock SSH only — use mock SSH/sapcontrol but real RAG, LLM, Langfuse
    mock_ssh: bool = Field(default=True, alias="MOCK_SSH")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def ssh_key_resolved(self) -> Path:
        return Path(self.ssh_key_path).expanduser()

    @property
    def use_mock_ssh(self) -> bool:
        """True when SSH tools should return mock data."""
        return self.demo_mode or self.mock_ssh


settings = Settings()

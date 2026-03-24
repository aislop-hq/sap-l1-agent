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

    # Demo mode
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def ssh_key_resolved(self) -> Path:
        return Path(self.ssh_key_path).expanduser()


settings = Settings()

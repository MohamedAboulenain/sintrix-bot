from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # NotebookLM
    notebooklm_notebook_id: str = ""
    nlm_daily_quota: int = 50
    nlm_quota_warning_threshold: int = 40

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # File storage
    sessions_dir: str = "data/sessions"
    temp_uploads_dir: str = "data/temp_uploads"
    max_upload_mb: int = 20

    # Server
    cors_origins: str = "http://localhost:8000,https://sintrix.io"
    log_level: str = "INFO"

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-large"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_API_KEY: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "client-knowledge"

    # Cosmos DB
    COSMOS_ENDPOINT: str = ""
    COSMOS_KEY: str = ""
    COSMOS_DB_NAME: str = "clientagent"

    # Application Insights
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = ""
    DISABLE_TELEMETRY: bool = False

    # OneDrive
    ONEDRIVE_SYNC_PATH: str = "/mnt/onedrive"

    # Auth
    ENTRA_CLIENT_ID: str = ""
    ENTRA_TENANT_ID: str = ""
    LOCAL_MODE: bool = False

    # MCP
    MCP_MS_LEARN_ENABLED: bool = False
    MCP_MS_LEARN_ENDPOINT: str = ""
    MCP_MS_GRAPH_ENABLED: bool = False
    MCP_MS_GRAPH_ENDPOINT: str = ""

    # Alerts
    ALERT_CHECK_INTERVAL: int = 900
    ALERT_RISK_THRESHOLD: int = 15
    ALERT_STALE_DAYS: int = 14

    # App
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def validate_azure_config(self):
        if not self.LOCAL_MODE:
            missing = []
            if not self.AZURE_OPENAI_ENDPOINT:
                missing.append("AZURE_OPENAI_ENDPOINT")
            if not self.AZURE_SEARCH_ENDPOINT:
                missing.append("AZURE_SEARCH_ENDPOINT")
            if not self.COSMOS_ENDPOINT:
                missing.append("COSMOS_ENDPOINT")
            if missing:
                raise ValueError(
                    f"Required in non-local mode: {', '.join(missing)}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

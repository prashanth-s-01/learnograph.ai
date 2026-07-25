from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    DATABASE_URL: str

    # LLM — provider-agnostic (currently TokenRouter, OpenAI-compatible)
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.tokenrouter.com/v1"
    LLM_MODEL: str = "anthropic/claude-sonnet-5"

    # mem0
    MEM0_API_KEY: str
    MEM0_USER_ID: str = "user_001"

    # Rtrvr.ai
    RTRVR_API_KEY: str

    # RocketRide — pipeline orchestration
    ROCKETRIDE_API_KEY: str = ""
    ROCKETRIDE_URI: str = "https://cloud.rocketride.ai"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    MODEL_NAME: str = "gemini-3.1-flash-lite"
    LOG_LEVEL: str = "INFO"

    # --- Profile acquisition ---
    PROFILE_MIN_DELAY_SECONDS: float = 1.5
    PROFILE_MAX_DELAY_SECONDS: float = 3.0
    PROFILE_CACHE_TTL_SECONDS: float = 300.0   # 5 minutes
    PROFILE_MAX_BATCH_SIZE: int = 10

    # --- Agent ---
    AGENT_MAX_TURNS: int = 6


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
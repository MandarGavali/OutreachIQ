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

    # --- PDF acquisition ---
    PDF_MAX_FILE_SIZE_MB: int = 10             # maximum upload size in megabytes

    # --- Agent ---
    AGENT_MAX_TURNS: int = 6

    # --- Self-Correction ---
    SELF_CORRECTION_ENABLED: bool = True
    SELF_CORRECTION_SCORE_THRESHOLD: float = 7.0  # 0–10; pass if score >= threshold
    MAX_SELF_CORRECTION_ATTEMPTS: int = 2          # max generation attempts (incl. first)


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://manga:manga@localhost:5432/manga_translator"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    debug: bool = False
    upload_dir: str = "uploads"
    ocr_low_confidence_threshold: float = 0.80
    prompt_file: str = "prompts/translate_page.v1.txt"
    cors_origins: list[str] = ["http://localhost:4200", "http://localhost:3000"]


settings = Settings()

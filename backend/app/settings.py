from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://manga:manga@localhost:5432/manga_translator"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    debug: bool = False
    upload_dir: str = "uploads"


settings = Settings()

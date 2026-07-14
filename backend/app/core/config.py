from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_EXPIRE_MINUTES: int = 60

    APP_TIMEZONE: str = "America/Sao_Paulo"

    ATTACHMENTS_DIR: str = "uploads"
    ATTACHMENTS_MAX_SIZE_BYTES: int = 10_485_760
    ATTACHMENTS_ALLOWED_CONTENT_TYPES: str = "image/png,image/jpeg,application/pdf,text/plain"

    DUE_SOON_CHECK_INTERVAL_SECONDS: int = 60
    DUE_SOON_WINDOW_HOURS: int = 24
    DUE_SOON_LOCK_KEY: int = 918273645

    @property
    def attachments_allowed_content_types_list(self) -> list[str]:
        return [
            content_type.strip()
            for content_type in self.ATTACHMENTS_ALLOWED_CONTENT_TYPES.split(",")
            if content_type.strip()
        ]


settings = Settings()

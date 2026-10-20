from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cookie_secure: bool = False
    session_days: int = 14
    login_attempts_per_minute: int = 5
    s3_endpoint: str = "http://storage:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "portfolio"
    max_upload_mb: int = 8


def get_settings() -> Settings:
    return Settings()

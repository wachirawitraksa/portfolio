from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cookie_secure: bool = False
    session_days: int = 14
    login_attempts_per_minute: int = 5


def get_settings() -> Settings:
    return Settings()

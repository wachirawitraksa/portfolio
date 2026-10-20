from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cookie_secure: bool = False
    session_days: int = 14
    login_attempts_per_minute: int = 5
    # GitHub OAuth is on only when all three are set. The redirect URI is
    # <admin host>/auth/github/callback, registered in the GitHub OAuth app.
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""
    # The question box. Without an API key it still works, in the "show me where to read" mode.
    gemini_api_key: str = ""
    gemini_model_cheap: str = "gemini-2.5-flash-lite"  # confident matches
    gemini_model_smart: str = "gemini-2.5-flash"  # partial matches, where wording matters more
    llm_timeout_seconds: int = 20
    ask_per_ip_per_day: int = 30
    ask_per_minute: int = 6
    ask_cache_days: int = 7
    ask_ip_salt: str = "portfolio"  # asks are logged with a salted hash of the IP, never the IP itself
    # Behind the Caddy proxy the real visitor is in X-Forwarded-For. Set false if the api is ever exposed directly.
    trust_forwarded_for: bool = True
    s3_endpoint: str = "http://storage:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "portfolio"
    max_upload_mb: int = 8


def get_settings() -> Settings:
    return Settings()

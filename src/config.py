from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = Field(validation_alias="DATABASE_URL")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    # JWT
    secret_key: str = Field(validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    # Email (SMTP)
    mail_username: str = Field(default="", validation_alias="MAIL_USERNAME")
    mail_password: str = Field(default="", validation_alias="MAIL_PASSWORD")
    mail_from: str = Field(default="noreply@unitalent.com", validation_alias="MAIL_FROM")
    mail_port: int = Field(default=587, validation_alias="MAIL_PORT")
    mail_server: str = Field(default="smtp.gmail.com", validation_alias="MAIL_SERVER")
    mail_starttls: bool = Field(default=True, validation_alias="MAIL_STARTTLS")
    mail_ssl_tls: bool = Field(default=False, validation_alias="MAIL_SSL_TLS")
    frontend_url: str = Field(default="http://localhost:8000", validation_alias="FRONTEND_URL")

    # CORS / TrustedHost
    cors_origins: list[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")
    trusted_hosts: list[str] = Field(default=["*"], validation_alias="TRUSTED_HOSTS")

    # Profiling
    profiling_enabled: bool = Field(default=False, validation_alias="PROFILING_ENABLED")
    slow_endpoint_threshold_ms: int = Field(default=500, validation_alias="SLOW_ENDPOINT_THRESHOLD_MS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

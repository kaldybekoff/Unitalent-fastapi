from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(validation_alias="DATABASE_URL")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    secret_key: str = Field(validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
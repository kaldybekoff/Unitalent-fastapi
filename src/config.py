from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(validation_alias="DATABASE_URL")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
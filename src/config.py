from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    mongodb_uri: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="portfolio_mcp", alias="MONGODB_DB_NAME")
    resume_drive_url: str | None = Field(default=None, alias="RESUME_DRIVE_URL")
    github_username: str = Field(default="", alias="GITHUB_USERNAME")
    leetcode_username: str = Field(default="", alias="LEETCODE_USERNAME")

@lru_cache()
def get_settings() -> Settings:
    return Settings()


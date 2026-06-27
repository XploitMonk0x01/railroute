from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RailRoute AI"
    api_version: str = "0.1.0"
    default_filter_preset: str = "default"
    default_top_k_routes: int = Field(default=5, ge=1, le=20)
    default_max_transfers: int = Field(default=2, ge=0, le=5)
    default_max_wait_min: int = Field(default=240, ge=0)
    transfer_penalty_min: int = Field(default=60, ge=0)
    database_url: str = "postgresql://master@127.0.0.1:5432/railroute"

    model_config = SettingsConfigDict(env_prefix="RAILROUTE_")


settings = Settings()

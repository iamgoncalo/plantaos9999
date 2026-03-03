"""Application settings using pydantic-settings.

Loads configuration from environment variables and .env files.
Provides typed access to all operational parameters.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Central application configuration.

    Values are loaded from environment variables and .env file.
    All fields have sensible defaults for development.
    """

    # App server
    APP_HOST: str = Field(default="0.0.0.0", description="Bind address")
    APP_PORT: int = Field(default=8050, description="HTTP port for the Dash server")
    DEBUG: bool = Field(
        default=True, description="Enable Dash debug mode with hot-reload"
    )
    LOG_LEVEL: str = Field(default="DEBUG", description="Logging level")

    # Data
    DATA_REFRESH_INTERVAL: int = Field(
        default=30, description="Dashboard auto-refresh interval in seconds"
    )
    SYNTHETIC_DAYS: int = Field(
        default=30, description="Days of synthetic history to generate"
    )
    DATA_SEED: int = Field(default=42, description="Random seed for reproducible data")

    # AI Insights
    ANTHROPIC_API_KEY: str = Field(
        default="", description="Anthropic API key for Claude insights"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = AppSettings()

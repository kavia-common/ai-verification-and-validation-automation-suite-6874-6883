"""
Environment configuration helpers for the backend API.

Reads values from environment and provides defaults. Supports loading a .env file
if present without failing when absent.
"""
import os
from dataclasses import dataclass
from typing import Optional


def _load_dotenv_if_present() -> None:
    """Load a .env file if python-dotenv is installed, else no-op."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # python-dotenv may not be installed; ignore silently
        pass


@dataclass
class EnvConfig:
    data_dir: str
    database_url: Optional[str]
    llm_provider: str
    llm_mock_mode: bool
    llm_api_key: Optional[str]


_config: Optional[EnvConfig] = None


def _init() -> EnvConfig:
    _load_dotenv_if_present()
    data_dir = os.getenv("DATA_DIR", "./data")
    os.makedirs(data_dir, exist_ok=True)
    database_url = os.getenv("DATABASE_URL")
    llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
    llm_mock_mode = os.getenv("LLM_MOCK", "true").lower() in ("1", "true", "yes", "y")
    llm_api_key = os.getenv("LLM_API_KEY")
    return EnvConfig(
        data_dir=data_dir,
        database_url=database_url,
        llm_provider=llm_provider,
        llm_mock_mode=llm_mock_mode,
        llm_api_key=llm_api_key,
    )


# PUBLIC_INTERFACE
def get_env() -> EnvConfig:
    """Return cached environment configuration, initializing if needed."""
    global _config
    if _config is None:
        _config = _init()
    return _config

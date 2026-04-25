from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "llama3.2:3b"
    service_port: int = int(os.getenv("SERVICE_PORT", 8123))
    service_name: str = "pm"
    base_fee: float = 1.75
    price_per_token: float = 0.0001
    price_per_minute: float = 0.01
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()



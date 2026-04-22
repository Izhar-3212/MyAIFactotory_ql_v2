# TODO: Implement config
#!/usr/bin/env python3
"""Centralized configuration with hardware awareness & validation."""

import os
import psutil
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # Ollama
    ollama_base_url: str = Field(default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_timeout: int = Field(default=int(os.getenv("OLLAMA_TIMEOUT", "300")))

    # Models
    default_model: str = Field(default=os.getenv("DEFAULT_MODEL", "qwen2.5-coder:7b"))
    planning_model: str = Field(default=os.getenv("PLANNING_MODEL", "llama3.2:3b"))
    backend_model: str = Field(default=os.getenv("BACKEND_MODEL", "qwen2.5-coder:7b"))
    frontend_model: str = Field(default=os.getenv("FRONTEND_MODEL", "qwen2.5-coder:7b"))
    qa_model: str = Field(default=os.getenv("QA_MODEL", "llama3.2:3b"))
    summarizer_model: str = Field(default=os.getenv("SUMMARIZER_MODEL", "llama3.2:3b"))

    # Limits & Paths
    max_context_chars: int = Field(default=int(os.getenv("MAX_CONTEXT_CHARS", "8000")))
    output_dir: str = Field(default=os.getenv("OUTPUT_DIR", "outputs"))
    state_file: str = Field(default=os.getenv("STATE_FILE", "orchestrator_state.json"))
    context_file: str = Field(default=os.getenv("CONTEXT_FILE", "orchestrator_context.md"))

    # Debug/Logging
    debug: bool = Field(default=os.getenv("DEBUG", "false").lower() == "true")
    log_format: str = Field(default=os.getenv("LOG_FORMAT", "console"))

    @field_validator("max_context_chars")
    @classmethod
    def validate_context(cls, v: int) -> int:
        if v < 1000:
            raise ValueError("MAX_CONTEXT_CHARS must be >= 1000")
        return v

    @property
    def output_path(self) -> Path: return Path(self.output_dir)
    @property
    def state_path(self) -> Path: return Path(self.state_file)
    @property
    def context_path(self) -> Path: return Path(self.context_file)

    @staticmethod
    def detect_hardware() -> dict:
        ram_gb = psutil.virtual_memory().total / (1024**3)
        rec = "llama3.2:3b" if ram_gb < 12 else "qwen2.5-coder:7b"
        return {"ram_gb": round(ram_gb, 1), "recommended_model": rec}

settings = Settings()
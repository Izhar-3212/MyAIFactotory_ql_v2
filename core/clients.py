#!/usr/bin/env python3
"""Async HTTP clients for agent services with retry logic."""

import os
import logging
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings

logger = logging.getLogger(__name__)

class ServiceClient:
    def __init__(self):
        self.base_timeout = settings.ollama_timeout
        self.services = {
            "planning": "http://localhost:8100/run",
            "backend": "http://localhost:8105/run",
            "frontend": "http://localhost:8106/run",
            "qa": "http://localhost:8107/run",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError))
    )
    async def call(self, service_name: str, context: str, instruction: Optional[str] = None, model: Optional[str] = None, timeout: Optional[int] = None, task_type: Optional[str] = None) -> str:
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        url = self.services[service_name]
        
        # Build payload based on service type
        if service_name == "planning":
            if not task_type:
                raise ValueError(f"task_type is required for planning service call (got: {service_name})")
            payload = {
                "task_type": task_type,
                "context": context,
                "instruction": instruction or ""
            }
        else:
            payload = {
                "context": context,
                "instruction": instruction or ""
            }
            if model:
                payload["model"] = model

        # ⏱️ TIMEOUT FIX: Code/QA services get 15 min, others use default
        if service_name in ["backend", "frontend", "qa"]:
            t = timeout or 1800  # 60 minutes
        else:
            t = timeout or self.base_timeout

        logger.debug(f"Calling {service_name} at {url} (timeout={t}s)")

        async with httpx.AsyncClient(timeout=t) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 422:
                logger.error(f"422 from {service_name}: {resp.text[:500]}")
            resp.raise_for_status()
            data = resp.json()
            if "output" not in data:
                raise ValueError(f"Invalid response from {service_name}: missing 'output' key")
            return data["output"]

class MCPFileWriter:
    """Secure file writer for generated code."""
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    async def write_file(self, path: str, content: str) -> bool:
        full_path = os.path.join(self.output_dir, path)
        os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
        tmp_path = full_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, full_path)
        logger.debug(f"File written: {full_path}")
        return True
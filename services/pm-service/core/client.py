# services/researcher-service/core/client.py
import httpx
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, config):
        self.base_url = config.ollama_base_url
        self.model = config.model_name
        self.timeout = 300  # 5 minutes
        
    async def generate(self, system_prompt: str, user_message: str, 
                      temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Call Ollama chat API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        },
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                raise
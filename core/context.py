# TODO: Implement context
#!/usr/bin/env python3
"""Context bounding with safe truncation & summarization hooks."""

import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self):
        self._context = ""
        self.max_chars = settings.max_context_chars

    def load(self) -> Optional[str]:
        if not settings.context_path.exists():
            return None
        try:
            self._context = settings.context_path.read_text(encoding="utf-8")
            logger.debug(f"Context loaded: {len(self._context)} chars")
            return self._context
        except Exception as e:
            logger.error(f"Context load failed: {e}")
            return None

    def save(self) -> bool:
        try:
            settings.context_path.parent.mkdir(parents=True, exist_ok=True)
            settings.context_path.write_text(self._context, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Context save failed: {e}")
            return False

    def append(self, text: str, source: str = "unknown") -> str:
        self._context += f"\n\n--- {source} Output ---\n{text}"
        self._enforce_limit()
        return self._context

    def get(self) -> str:
        return self._context

    def set(self, text: str) -> None:
        self._context = text
        self._enforce_limit()

    async def summarize_and_replace(self, new_text: str, source: str, summarizer_fn) -> str:
        """Accepts an async callable that performs the LLM summarization."""
        combined = f"{self._context}\n\n--- New {source} Output ---\n{new_text}"
        if len(combined) <= self.max_chars:
            self._context = combined
            return self._context

        try:
            summary = await summarizer_fn(combined, source)
            self._context = summary.strip()
            logger.info(f"Context summarized via agent ({len(self._context)} chars)")
        except Exception as e:
            logger.warning(f"Summarization failed, falling back to truncation: {e}")
            self._context = self._truncate(combined)
        return self._context

    def _enforce_limit(self) -> None:
        if len(self._context) > self.max_chars:
            self._context = self._truncate(self._context)

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_chars:
            return text
        cut = text[:self.max_chars].rsplit("\n", 1)[0]
        return cut + "\n...[context truncated]" if cut else text[:self.max_chars] + "..."
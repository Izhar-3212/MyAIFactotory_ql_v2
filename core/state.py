# TODO: Implement state
#!/usr/bin/env python3
"""Atomic state management with crash recovery & resume support."""

import os
import json
import shutil
import tempfile
import logging
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timezone
from core.config import settings

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self):
        self.state_path = settings.state_path
        self.backup_dir = self.state_path.parent / ".state_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {
                **raw,
                "completed_steps": set(raw.get("completed_steps", [])),
                # NEW (keeps as dicts):
                "tasks": raw.get("tasks") if raw.get("tasks") else None,
            }
        except Exception as e:
            logger.warning(f"State load failed, attempting backup: {e}")
            return self._recover_from_backup()

    def save(self, step: str, completed: Set[str], tasks: Optional[List[tuple]] = None, idx: int = 0) -> bool:
        state = {
            "last_step": step,
            "completed_steps": list(completed),
            "tasks": [list(t) if isinstance(t, (list, tuple)) else t for t in tasks] if tasks else None,
            "task_index": idx,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": 2
        }
        try:
            fd, tmp_path = tempfile.mkstemp(dir=self.state_path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            if self.state_path.exists():
                backup_name = f"state_{datetime.now():%Y%m%d_%H%M%S}.json"
                shutil.copy2(self.state_path, self.backup_dir / backup_name)
            shutil.move(tmp_path, str(self.state_path))
            logger.debug(f"State saved atomically: {step}")
            return True
        except Exception as e:
            logger.error(f"State save failed: {e}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False

    def clear(self) -> None:
        for p in [self.state_path, settings.context_path]:
            if p.exists():
                p.unlink()
        logger.info("State & context files cleared.")

    def _recover_from_backup(self) -> Optional[Dict[str, Any]]:
        backups = sorted(self.backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            return None
        try:
            with open(backups[0], "r", encoding="utf-8") as f:
                raw = json.load(f)
            raw["completed_steps"] = set(raw.get("completed_steps", []))
            raw["tasks"] = [tuple(t) for t in raw.get("tasks", [])] if raw.get("tasks") else None
            logger.info(f"State recovered from backup: {backups[0].name}")
            return raw
        except Exception as e:
            logger.error(f"Backup recovery failed: {e}")
            return None
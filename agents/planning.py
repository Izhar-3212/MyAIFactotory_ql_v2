# Suppress noisy CrewAI EventBus warnings (non-fatal)
import logging
logging.getLogger("crewai.agents.event_bus").setLevel(logging.ERROR)
#!/usr/bin/env python3
"""Planning Service: Research, BA, Architect, PM, Summarizer"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, LLM
from core.config import settings

app = FastAPI(title="Planning Service")
logger = logging.getLogger(__name__)

PROMPT_DIR = Path("prompts")
TASKS = {
    "researcher": {"file": "research.md", "model": settings.planning_model},
    "ba": {"file": "ba.md", "model": settings.planning_model},
    "architect": {"file": "architect.md", "model": settings.planning_model},
    "pm": {"file": "pm.md", "model": settings.planning_model},
    "summarizer": {"file": "summarizer.md", "model": settings.summarizer_model},
}

class RunRequest(BaseModel):
    task_type: str
    context: str
    instruction: str | None = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "planning", "port": 8100}

@app.post("/run")
async def run(req: RunRequest):
    if req.task_type not in TASKS:
        raise HTTPException(400, f"Unknown task_type: {req.task_type}")
        
    cfg = TASKS[req.task_type]
    prompt_path = PROMPT_DIR / cfg["file"]
    if not prompt_path.exists():
        raise HTTPException(500, f"Prompt not found: {prompt_path}")
        
    prompt_text = prompt_path.read_text(encoding="utf-8")
    full_prompt = f"{prompt_text}\n\nCONTEXT:\n{req.context[:settings.max_context_chars]}"
    if req.instruction:
        full_prompt += f"\n\nINSTRUCTION:\n{req.instruction}"

    # DEBUG: Log exactly what model name is being used
    model_name = f"ollama_chat/{cfg['model']}"
    logger.debug(f"LLM INIT: model='{model_name}', base_url='{settings.ollama_base_url}'")
    
    # CORRECT LLM CONFIG FOR OLLAMA + CREWAI + LITELLM
    llm = LLM(
        model=model_name,
        base_url=settings.ollama_base_url,
        api_key="ollama",
        temperature=0.3,
        max_tokens=8192,
        timeout=3600
    )
    
    agent = Agent(
        role=cfg["file"].replace(".md", "").replace("_", " ").title(),
        goal="Execute task accurately and concisely",
        backstory="Expert AI assistant specializing in technical documentation and planning",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2
    )
    
    task = Task(
        description=full_prompt,
        expected_output="Complete output matching prompt requirements",
        agent=agent
    )
    
    try:
        logger.debug(f"Executing {req.task_type} (model={cfg['model']})")
        result = task.execute_sync()
        return {"output": result.raw.strip()}
    except Exception as e:
        logger.error(f"Planning task failed: {type(e).__name__}: {e}")
        raise HTTPException(500, str(e))
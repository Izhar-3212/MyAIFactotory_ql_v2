# Suppress noisy CrewAI EventBus warnings (non-fatal)
import logging
logging.getLogger("crewai.agents.event_bus").setLevel(logging.ERROR)
#!/usr/bin/env python3
"""Frontend Coder Service: Generates responsive frontend code"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, LLM
from core.config import settings

app = FastAPI(title="Frontend Coder")
logger = logging.getLogger(__name__)

PROMPT_DIR = Path("prompts")

class RunRequest(BaseModel):
    context: str
    instruction: str | None = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "frontend_coder", "port": 8106}

@app.post("/run")
async def run(req: RunRequest):
    prompt_path = PROMPT_DIR / "frontend_coder.md"
    if not prompt_path.exists():
        raise HTTPException(500, f"Prompt not found: {prompt_path}")
        
    prompt_text = prompt_path.read_text(encoding="utf-8")
    full_prompt = f"{prompt_text}\n\nCONTEXT:\n{req.context[:settings.max_context_chars]}"
    if req.instruction:
        full_prompt += f"\n\nTASK:\n{req.instruction}"

    model_name = f"ollama_chat/{settings.frontend_model}"
    logger.debug(f"LLM INIT: model='{model_name}', base_url='{settings.ollama_base_url}'")
    
    llm = LLM(
        model=model_name,
        base_url=settings.ollama_base_url,
        api_key="ollama",
        temperature=0.3,
        max_tokens=8192,
        timeout=3600
    )
    
    agent = Agent(
        role="UI/UX Developer",
        goal="Build responsive, accessible frontend components",
        backstory="Frontend expert specializing in modern frameworks and UX best practices",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2
    )
    
    task = Task(
        description=full_prompt,
        expected_output="Markdown code blocks with file paths",
        agent=agent
    )
    
    try:
        logger.debug(f"Generating frontend code (model={settings.frontend_model})")
        result = task.execute_sync()
        return {"output": result.raw.strip()}
    except Exception as e:
        logger.error(f"Frontend generation failed: {type(e).__name__}: {e}")
        raise HTTPException(500, str(e))
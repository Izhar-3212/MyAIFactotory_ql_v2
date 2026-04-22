#!/usr/bin/env python3
# Suppress noisy CrewAI EventBus warnings (non-fatal)
import logging
logging.getLogger("crewai.agents.event_bus").setLevel(logging.ERROR)
"""QA Tester Service: Generates executable tests & JSON summaries"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, LLM
from core.config import settings

app = FastAPI(title="QA Tester")
logger = logging.getLogger(__name__)

PROMPT_DIR = Path("prompts")

class RunRequest(BaseModel):
    context: str
    instruction: str | None = None

@app.get("/health")
async def health():
    return {"status": "ok", "service": "qa_tester", "port": 8107}

@app.post("/run")
async def run(req: RunRequest):
    prompt_path = PROMPT_DIR / "qa_tester.md"
    if not prompt_path.exists():
        raise HTTPException(500, f"Prompt not found: {prompt_path}")
        
    prompt_text = prompt_path.read_text(encoding="utf-8")
    # QA needs less context to avoid confusion with JSON output
    full_prompt = f"{prompt_text}\n\nCONTEXT:\n{req.context[:2000]}"
    if req.instruction:
        full_prompt += f"\n\nTASK:\n{req.instruction}"

    model_name = f"ollama_chat/{settings.qa_model}"
    logger.debug(f"LLM INIT: model='{model_name}', base_url='{settings.ollama_base_url}'")
    
    llm = LLM(
        model=model_name,
        base_url=settings.ollama_base_url,
        api_key="ollama",
        temperature=0.2,
        max_tokens=4096,
        timeout=3600
    )
    
    agent = Agent(
        role="QA Automation Engineer",
        goal="Write executable tests and accurate JSON summaries",
        backstory="Senior QA specialist focused on test coverage and bug detection",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2
    )
    
    task = Task(
        description=full_prompt,
        expected_output="Test code + JSON summary",
        agent=agent
    )
    
    try:
        logger.debug(f"Generating QA tests (model={settings.qa_model})")
        result = task.execute_sync()
        return {"output": result.raw.strip()}
    except Exception as e:
        logger.error(f"QA generation failed: {type(e).__name__}: {e}")
        raise HTTPException(500, str(e))
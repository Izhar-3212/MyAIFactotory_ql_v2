from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
import requests
from datetime import datetime

app = FastAPI(title="QA Tester Agent", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OLLAMA_HOST = "http://localhost:11434"
MODEL = "deepseek-coder:1.3b"

class AgentRequest(BaseModel):
    project_idea: str = Field(..., min_length=10)
    domain: Optional[str] = "software-dev"
    customer_id: Optional[str] = None
    project_id: Optional[str] = None

def call_ollama(system_prompt: str, user_prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 4096}
            },
            timeout=3600
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama is not running. Start it with 'ollama serve'.")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Ollama request timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

@app.post("/run")
async def run(req: AgentRequest):
    try:
        logger.info(f"[{req.project_id}] QA Tester calling Ollama ({MODEL})...")
        system_prompt = """You are a senior QA engineer specializing in automated testing, edge case discovery, and quality assurance.
        Generate a comprehensive testing strategy for the given project. Output strictly in markdown with:
        1. 🎯 Scope-to-Test Mapping (primary goal, methodology, coverage)
        2. 📋 Test Pyramid & Execution Plan (unit, integration, E2E breakdown)
        3. 🛠️ Core Test Implementation Snippets (pytest, Playwright examples)
        4. 📊 CI/CD Pipeline & Automation (GitHub Actions YAML)
        5. ✅ Deliverables & Handoff Checklist (coverage targets, sign-off criteria)
        Focus on practical, runnable tests with clear assertions. Prioritize critical paths and security edge cases. Do not include explanations outside the markdown structure."""

        user_prompt = f"Project Idea: {req.project_idea}\nDomain: {req.domain}"

        output = call_ollama(system_prompt, user_prompt)
        return {"output": output, "status": "completed", "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{req.project_id}] QA Tester failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "QA Tester Agent", "model": MODEL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8126)

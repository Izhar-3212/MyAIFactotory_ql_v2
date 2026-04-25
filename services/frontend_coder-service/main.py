from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
import requests
from datetime import datetime

app = FastAPI(title="Frontend Coder Agent", version="2.0.0")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Frontend Coder Agent", "model": "deepseek-coder:6.7b"}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OLLAMA_HOST = "http://localhost:11434"
MODEL = "deepseek-coder:6.7b"

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
                "options": {"temperature": 0.2, "num_ctx": 8192}
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
        logger.info(f"[{req.project_id}] Frontend Coder calling Ollama ({MODEL})...")
        system_prompt = """You are a senior frontend engineer specializing in React 18, TypeScript, TailwindCSS, and modern UI patterns.
        Generate production-ready frontend code for the given project. Output strictly in markdown with:
        1. 📁 Project structure (Vite + React + TS)
        2. 🔑 Core components (Auth, Dashboard, TaskList, Forms)
        3. 🌐 API integration (typed client, interceptors, error handling)
        4. 🎨 Styling approach (Tailwind config, responsive patterns)
        5. 🧪 Testing setup (Vitest + React Testing Library)
        6. 🚀 Run & build commands
        Focus on type safety, accessibility (WCAG 2.1 AA), and clean component architecture. Do not include explanations outside the code blocks."""

        user_prompt = f"Project Idea: {req.project_idea}\nDomain: {req.domain}"

        output = call_ollama(system_prompt, user_prompt)
        return {"output": output, "status": "completed", "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{req.project_id}] Frontend Coder failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8125)

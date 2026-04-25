from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import requests
import sys
import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from services.shared.github_client import GitHubClient

app = FastAPI(title="Project Manager Agent", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OLLAMA_HOST = "http://localhost:11434"
MODEL = "llama3.2:3b"

class AgentRequest(BaseModel):
    project_idea: str = Field(..., min_length=10)
    domain: Optional[str] = "software-dev"
    customer_id: Optional[str] = None
    project_id: Optional[str] = None
    enable_github: bool = False

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
                "options": {"temperature": 0.3, "num_ctx": 4096}
            },
            timeout=3600
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama is not running.")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Ollama request timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

def parse_user_stories(pm_output: str) -> List[tuple]:
    stories = []
    patterns = [
        r'- \[(US-\d+)\]\s*(HIGH|MED|LOW):\s*(.+?)(?=\n- \[|\n##|\Z)',
        r'\*?\s*(US-\d+).*?(HIGH|MED|LOW)[:\s]+(.+?)(?=\n\*|\n##|\Z)',
    ]
    for pattern in patterns:
        found = re.findall(pattern, pm_output, re.IGNORECASE | re.DOTALL)
        if found:
            for item in found:
                sid = item[0] if len(item) > 0 else "US-1"
                prio = (item[1] if len(item) > 1 else "HIGH").upper()
                desc = (item[2] if len(item) > 2 else "Task").strip()
                stories.append((sid, prio, desc))
            break
    if not stories:
        stories = [("US-1", "HIGH", "Initial project setup")]
    return stories[:10]

@app.post("/run")
async def run(req: AgentRequest):
    print(f"DEBUG: enable_github={req.enable_github}")
    try:
        logger.info(f"[{req.project_id}] PM calling Ollama ({MODEL})...")
        system_prompt = """You are a senior project manager.
        Generate a project execution plan. Output STRICTLY in markdown with:
        1. Scope & Methodology
        2. Sprint Breakdown
        3. User Stories (format: "- [US-1] HIGH: As a user, I can...")
        4. Risk Matrix
        5. Milestones
        RULES: No intro text. Start with "# Project Execution Plan"."""
        user_prompt = f"Project Idea: {req.project_idea}\nDomain: {req.domain}"
        pm_output = call_ollama(system_prompt, user_prompt)

        github_info: Dict[str, Any] = {
            "enabled": False, "repo_url": None, "project_url": None,
            "issues_created": 0, "project_id": None
        }

        enable_flag = str(getattr(req, "enable_github", False)).lower()
        if enable_flag not in ["true", "1", "yes"]:
            return {"output": pm_output, "status": "completed", "github": github_info, "timestamp": datetime.now(timezone.utc).isoformat()}

        logger.info("GitHub integration ACTIVATED")
        gh = GitHubClient()
        if not gh.is_configured():
            github_info["error"] = "GitHub credentials missing"
            return {"output": pm_output, "status": "completed", "github": github_info, "timestamp": datetime.now(timezone.utc).isoformat()}

        try:
            repo_name = (req.project_id or "ai-factory-project").replace("proj_", "repo_")
            repo_resp = gh.create_repo(repo_name, req.project_idea[:100])
            repo_url = repo_resp.get("html_url")
            logger.info(f"Repo: {repo_url}")

            # DEBUG: Print project creation result
            project_resp = gh.create_project_v2(f"{req.project_idea[:30]} Board", repo_name)
            print(f"DEBUG: project_resp type={type(project_resp)}")
            print(f"DEBUG: project_resp value={project_resp}")
            
            project_url = None
            project_id = None
            if project_resp and isinstance(project_resp, dict) and project_resp.get("url"):
                project_url = project_resp.get("url")
                project_id = project_resp.get("id")
                logger.info(f"Project Board: {project_url}")

            stories = parse_user_stories(pm_output)
            issues_created = 0
            for story_id, priority, desc in stories:
                try:
                    issue = gh.create_issue(repo_name, f"{story_id}: {desc[:80]}", f"Priority: {priority}\n\n{desc}", labels=[priority.lower()])
                    issue_num = issue.get("number")
                    if issue_num and project_id:
                        gh.add_issue_to_project(repo_name, issue_num, project_id)
                    issues_created += 1
                except Exception as ie:
                    logger.warning(f"Issue failed: {ie}")

            github_info = {
                "enabled": True, "repo_url": repo_url, "project_url": project_url,
                "issues_created": issues_created, "project_id": project_id
            }
            logger.info(f"GitHub complete: {issues_created} issues")

        except Exception as e:
            import traceback
            logger.error(f"GitHub failed: {e}\n{traceback.format_exc()}")
            github_info["error"] = str(e)

        return {"output": pm_output, "status": "completed", "github": github_info, "timestamp": datetime.now(timezone.utc).isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PM failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Project Manager Agent", "model": MODEL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8123)

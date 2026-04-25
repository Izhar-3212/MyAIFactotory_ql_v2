from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import httpx, logging
from datetime import datetime

app = FastAPI(title="AI Factory Orchestrator", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SERVICES = {
    "researcher": "http://localhost:8120",
    "ba": "http://localhost:8121",
    "architect": "http://localhost:8122",
    "pm": "http://localhost:8123",
    "backend_coder": "http://localhost:8124",
    "frontend_coder": "http://localhost:8125",
    "qa_tester": "http://localhost:8126",
    "integrator": "http://localhost:8127"
}

class ProjectRequest(BaseModel):
    enable_github: bool = False
    project_idea: str = Field(..., min_length=10)
    selected_agents: List[str] = Field(..., min_items=1)
    domain: Optional[str] = "software-dev"
    customer_id: Optional[str] = None
    iterations: Optional[int] = 1

class ProjectResponse(BaseModel):
    project_id: str
    status: str
    outputs: Dict[str, str]
    customer_billing: Dict
    timestamp: str
    github_integration: Optional[Dict] = None

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "orchestrator", "version": "2.0.0"}

@app.post("/run", response_model=ProjectResponse)
async def run_project(req: ProjectRequest):
    project_id = f"proj_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    outputs = {}
    github_integration = {}
    logger.info(f"[{project_id}] Starting with agents: {req.selected_agents}")

    async with httpx.AsyncClient(timeout=3600) as client:
        for agent in req.selected_agents:
            if agent not in SERVICES:
                raise HTTPException(status_code=400, detail=f"Unknown agent: {agent}")
            try:
                resp = await client.post(f"{SERVICES[agent]}/run", json={
                    "project_idea": req.project_idea, "domain": req.domain,
                    "customer_id": req.customer_id, "project_id": project_id,
        "enable_github": req.enable_github
                })
                resp.raise_for_status()
                agent_resp = response.json()
                outputs[agent] = agent_resp.get("output", "")
                if agent_resp.get("github"):
                    github_integration[agent] = agent_resp["github"]
                logger.info(f"[{project_id}] {agent} completed")
            except Exception as e:
                logger.error(f"[{project_id}] {agent} failed: {e}")
                outputs[agent] = f"ERROR: {e}"

    agent_count = len(req.selected_agents)
    iteration_count = req.iterations or 1
    total = round(10.00 + (agent_count * 5.00) + (iteration_count * 2.00), 2)

    customer_billing = {
        "signup_fee": 10.00,
        "agent_count": agent_count,
        "agent_fee_per_unit": 5.00,
        "iteration_count": iteration_count,
        "iteration_fee_per_unit": 2.00,
        "total_amount": total,
        "currency": "USD",
        "formula": f"$10 + ({agent_count} agents x $5) + ({iteration_count} iterations x $2) = ${total}"
    }

    return ProjectResponse(
        project_id=project_id, status="completed", outputs=outputs,
        customer_billing=customer_billing, timestamp=datetime.utcnow().isoformat(), github_integration=github_integration if github_integration else None
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

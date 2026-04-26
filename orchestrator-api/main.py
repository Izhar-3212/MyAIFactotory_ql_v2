from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx, logging
from datetime import datetime, timezone

app = FastAPI(title="AI Factory Orchestrator", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SERVICES = {
    "researcher": "http://localhost:8120", "ba": "http://localhost:8121",
    "architect": "http://localhost:8122", "pm": "http://localhost:8123",
    "backend_coder": "http://localhost:8124", "frontend_coder": "http://localhost:8125",
    "qa_tester": "http://localhost:8126", "integrator": "http://localhost:8127"
}

PLANNING_AGENTS = ["researcher", "ba", "architect", "pm"]
CODING_AGENTS = ["backend_coder", "frontend_coder", "qa_tester"]

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
    outputs: Dict[str, Any]
    customer_billing: Dict
    timestamp: str
    github_integration: Optional[Dict] = None

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "orchestrator", "version": "2.0.0"}

@app.post("/run", response_model=ProjectResponse)
async def run_project(req: ProjectRequest):
    project_id = f"proj_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    outputs = {}
    github_integration = {}
    context = f"# Project Context\n\n**Idea**: {req.project_idea}\n**Domain**: {req.domain}\n"
    logger.info(f"[{project_id}] Starting sequential pipeline: {req.selected_agents}")

    async with httpx.AsyncClient(timeout=3600) as client:
        # PHASE 1: Sequential Planning
        for agent in PLANNING_AGENTS:
            if agent not in req.selected_agents or agent not in SERVICES: continue
            try:
                ctx_idea = f"{req.project_idea}\n\n---\n[PREVIOUS CONTEXT]\n{context}\n---\n"
                resp = await client.post(f"{SERVICES[agent]}/run", json={
                    "project_idea": ctx_idea, "domain": req.domain,
                    "customer_id": req.customer_id, "project_id": project_id,
                    "enable_github": req.enable_github})
                resp.raise_for_status()
                agent_resp = resp.json()
                outputs[agent] = agent_resp.get("output", "")
                # DEBUG: Log what we're storing
                print(f"🔍 DEBUG [{project_id}] {agent}: output_len={len(outputs[agent])}, keys={list(agent_resp.keys())}")
                context += f"\n\n## {agent.upper()} OUTPUT\n{outputs[agent]}\n"
                #context += f"\n\n## {agent.upper()} OUTPUT\n{outputs[agent]}\n"
                if agent_resp.get("github"): github_integration[agent] = agent_resp["github"]
                logger.info(f"[{project_id}] {agent} completed")
            except Exception as e:
                logger.error(f"[{project_id}] {agent} failed: {e}")
                outputs[agent] = f"ERROR: {str(e)}"

        # PHASE 2: Parallel Coding
        coding_selected = [a for a in req.selected_agents if a in CODING_AGENTS]
        if coding_selected:
            tasks = []
            for agent in coding_selected:
                if agent not in SERVICES: continue
                ctx_idea = f"{req.project_idea}\n\n---\n[PLANNING CONTEXT]\n{context}\n---\n"
                tasks.append(client.post(f"{SERVICES[agent]}/run", json={
                    "project_idea": ctx_idea, "domain": req.domain,
                    "customer_id": req.customer_id, "project_id": project_id,
                    "enable_github": req.enable_github}))
            results = await httpx.gather(*tasks, return_exceptions=True)
            for agent, result in zip(coding_selected, results):
                if isinstance(result, Exception):
                    logger.error(f"[{project_id}] {agent} failed: {result}")
                    outputs[agent] = f"ERROR: {str(result)}"
                else:
                    agent_resp = result.json()
                    outputs[agent] = agent_resp.get("output", "")
                    if agent_resp.get("github"): github_integration[agent] = agent_resp["github"]
                    logger.info(f"[{project_id}] {agent} completed")

        # PHASE 3: Integrator
        if "integrator" in req.selected_agents and "integrator" in SERVICES:
            try:
                ctx_idea = f"{req.project_idea}\n\n---\n[FULL CONTEXT]\n{context}\n---\n"
                resp = await client.post(f"{SERVICES['integrator']}/run", json={
                    "project_idea": ctx_idea, "domain": req.domain,
                    "customer_id": req.customer_id, "project_id": project_id,
                    "enable_github": req.enable_github})
                resp.raise_for_status()
                agent_resp = resp.json()
                outputs["integrator"] = agent_resp.get("output", "")
                if agent_resp.get("github"): github_integration["integrator"] = agent_resp["github"]
                logger.info(f"[{project_id}] integrator completed")
            except Exception as e:
                logger.error(f"[{project_id}] integrator failed: {e}")
                outputs["integrator"] = f"ERROR: {str(e)}"

    # Billing
    agent_count = len(req.selected_agents)
    iteration_count = req.iterations or 1
    total = round(10.00 + (agent_count * 5.00) + (iteration_count * 2.00), 2)
    customer_billing = {
        "signup_fee": 10.00, "agent_count": agent_count, "agent_fee_per_unit": 5.00,
        "iteration_count": iteration_count, "iteration_fee_per_unit": 2.00,
        "total_amount": total, "currency": "USD",
        "formula": f"$10 + ({agent_count} agents x $5) + ({iteration_count} iterations x $2) = ${total}"
    }

        # DEBUG + FIX: Ensure outputs serializes correctly for Pydantic
    print(f"🔍 FINAL outputs dict: {outputs}")
    print(f"🔍 FINAL outputs types: {[(k, type(v).__name__) for k,v in outputs.items()]}")
    outputs = {k: str(v) if v is not None else "" for k, v in outputs.items()}
    
    return ProjectResponse(
        project_id=project_id, status="completed", outputs=outputs,
        customer_billing=customer_billing, timestamp=datetime.now(timezone.utc).isoformat(),
        github_integration=github_integration if github_integration else None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
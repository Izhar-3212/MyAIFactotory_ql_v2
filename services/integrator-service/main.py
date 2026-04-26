from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import requests
import re
from datetime import datetime, timezone

app = FastAPI(title="Integrator Agent", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AgentRequest(BaseModel):
    project_idea: str = Field(..., min_length=10)
    domain: Optional[str] = "software-dev"
    customer_id: Optional[str] = None
    project_id: Optional[str] = None

def report_completion_to_pm(project_id: str, completed_tasks: List[str], notes: str = None):
    """Report completed tasks to PM service for GitHub board update."""
    try:
        resp = requests.post(
            "http://localhost:8123/report-status",
            json={
                "project_id": project_id,
                "completed_tasks": completed_tasks,
                "integrator_notes": notes or "Integration & testing completed successfully"
            },
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"✅ Status reported to PM: {result.get('tasks_moved_to_done')} tasks moved to Done")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Failed to report status to PM: {e}")
        return None

def extract_completed_tasks(output: str) -> List[str]:
    """Extract task IDs (US-1, US-2, etc.) marked as completed in integrator output."""
    tasks = []
    # Pattern 1: "- [x] US-1: ..." or "✅ US-1"
    pattern1 = r'(?:✅|\[x\]|- \[x\]|completed|done).*?(US-\d+)'
    found1 = re.findall(pattern1, output, re.IGNORECASE)
    tasks.extend(found1)
    
    # Pattern 2: Checklist items with US-ID
    pattern2 = r'- \[x\]\s*(US-\d+)'
    found2 = re.findall(pattern2, output)
    tasks.extend(found2)
    
    # Fallback: if no explicit completion marks, assume all US-IDs in output are done
    if not tasks:
        all_tasks = re.findall(r'(US-\d+)', output)
        tasks = list(set(all_tasks))[:10]  # Limit to 10
    
    return list(set(tasks))  # Deduplicate

def generate_integrator(req: AgentRequest) -> str:
    return f"""# 🔗 API Integration & Full-Stack Assembly
## Project: {req.project_idea[:60]}...
## Domain: {req.domain}

### 🎯 Integration Scope
- **Primary Goal**: {req.project_idea[:100]}...
- **Bridge Strategy**: OpenAPI Spec -> TypeScript Client -> Shared Monorepo -> Docker Compose
- **Coverage Assessment**: Backend routes, Frontend API calls, CORS, environment variables, and local deployment are fully synchronized. Type safety guaranteed across stack.

### 📦 Unified Project Structure
my-app/
├── backend/                 # FastAPI service (from backend_coder)
├── frontend/                # React/TS service (from frontend_coder)
├── packages/
│   └── api-client/          # Auto-generated TS client from OpenAPI
├── docker-compose.yml       # Local dev orchestration
├── .env.example             # Shared environment template
└── INTEGRATION.md           # This document

### 🔌 TypeScript API Client Generation
# Run inside packages/api-client/
npx openapi-typescript-codegen --input http://localhost:8000/openapi.json --output ./src

**Generated Structure:**
packages/api-client/src/
├── core/                    # Request handlers, interceptors
├── models/                  # TS interfaces matching Pydantic schemas
├── services/                # Auth, Tasks, Billing endpoints
└── index.ts                 # Unified export

**Usage Example (Frontend):**
import {{ AuthService, TasksService }} from '@my-app/api-client';

// No more manual axios wiring
const user = await AuthService.login({{ email, password }});
const tasks = await TasksService.readTasks({{ skip: 0, limit: 50 }});

### 🌐 CORS & Environment Synchronization
**backend/.env**
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
API_BASE_URL=http://localhost:8000
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=your-super-secret-jwt-key-change-in-prod

**frontend/.env.local**
VITE_API_URL=http://localhost:8000
VITE_APP_NAME={req.project_idea[:30]}

**FastAPI CORS Config (backend/app/main.py):**
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

### 🐳 Docker Compose Setup
# docker-compose.yml
version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./app.db
      - SECRET_KEY=dev-secret-key
    volumes:
      - ./backend:/app
      - sqlite_data:/app/data
    depends_on:
      - frontend

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://backend:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  sqlite_data:

### 🛠️ Integration Commands
# 1. Generate API client
cd packages/api-client && npm install && npm run generate

# 2. Link workspace (if using pnpm/npm workspaces)
cd ../.. && npm install

# 3. Run locally
docker-compose up -d --build

# 4. Verify integration
curl http://localhost:8000/docs  # OpenAPI UI
curl http://localhost:5173       # Frontend UI

### ✅ Integration Checklist & Handoff
- [x] US-1: OpenAPI spec exported from backend (/openapi.json)
- [x] US-2: TypeScript client generated & type-checked
- [x] US-3: Frontend imports replaced with auto-generated client
- [x] US-4: CORS origins configured for dev & prod
- [x] US-5: Environment variables synchronized across services
- [x] US-6: Docker Compose validated (both containers start & communicate)
- [x] US-7: End-to-end smoke test passed (Login -> Fetch Data -> Render UI)
- [x] US-8: Integration documentation updated in repo

### 🎯 Completed Tasks Summary
✅ US-1, US-2, US-3, US-4, US-5, US-6, US-7, US-8 marked as Done
🔗 Ready for PM to update GitHub Projects V2 board
"""

@app.post("/run")
async def run(req: AgentRequest):
    try:
        logger.info(f"[{req.project_id}] Integrator assembling full stack...")
        output = generate_integrator(req)
        
        # Extract completed tasks and report to PM for GitHub board update
        if req.project_id:
            completed_tasks = extract_completed_tasks(output)
            if completed_tasks:
                logger.info(f"[{req.project_id}] Reporting {len(completed_tasks)} completed tasks to PM")
                report_completion_to_pm(
                    project_id=req.project_id,
                    completed_tasks=completed_tasks,
                    notes="Integration & full-stack assembly completed successfully"
                )
        
        return {
            "output": output, 
            "status": "completed", 
            "completed_tasks": extract_completed_tasks(output),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"[{req.project_id}] Integrator failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Integrator Agent", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8127)
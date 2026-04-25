from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

app = FastAPI(title="Integrator Agent", version="2.0.0")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AgentRequest(BaseModel):
    project_idea: str = Field(..., min_length=10)
    domain: Optional[str] = "software-dev"
    customer_id: Optional[str] = None
    project_id: Optional[str] = None

@app.post("/run")
async def run(req: AgentRequest):
    try:
        logger.info(f"[{req.project_id}] Integrator assembling full stack...")
        output = generate_integrator(req)
        return {"output": output, "status": "completed", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"[{req.project_id}] Integrator failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
- [ ] OpenAPI spec exported from backend (/openapi.json)
- [ ] TypeScript client generated & type-checked
- [ ] Frontend imports replaced with auto-generated client
- [ ] CORS origins configured for dev & prod
- [ ] Environment variables synchronized across services
- [ ] Docker Compose validated (both containers start & communicate)
- [ ] End-to-end smoke test passed (Login -> Fetch Data -> Render UI)
- [ ] Integration documentation updated in repo
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8127)

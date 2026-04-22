@echo off
echo 🚀 Starting SpecForge Agent Services...
start "Planning" cmd /k "cd /d %~dp0 & .\.venv\Scripts\activate & uvicorn agents.planning:app --port 8100 --reload"
start "Backend" cmd /k "cd /d %~dp0 & .\.venv\Scripts\activate & uvicorn agents.backend_coder:app --port 8105 --reload"
start "Frontend" cmd /k "cd /d %~dp0 & .\.venv\Scripts\activate & uvicorn agents.frontend_coder:app --port 8106 --reload"
start "QA" cmd /k "cd /d %~dp0 & .\.venv\Scripts\activate & uvicorn agents.qa_tester:app --port 8107 --reload"
echo ✅ All services starting. Run `python main.py` to begin orchestration.
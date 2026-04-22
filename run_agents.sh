#!/bin/bash
echo "🚀 Starting SpecForge Agent Services..."
tmux new-session -d -s planning ". .venv/bin/activate && uvicorn agents.planning:app --port 8100 --reload"
tmux split-window -h ". .venv/bin/activate && uvicorn agents.backend_coder:app --port 8105 --reload"
tmux split-window -v ". .venv/bin/activate && uvicorn agents.frontend_coder:app --port 8106 --reload"
tmux split-window -v ". .venv/bin/activate && uvicorn agents.qa_tester:app --port 8107 --reload"
echo "✅ All services started. Run `python main.py` to begin orchestration."
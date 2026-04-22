#!/usr/bin/env python3
"""Launcher v5 - Robust .venv path detection."""
import os, sys, subprocess, time, threading
from pathlib import Path

SERVICES = [
    {"name": "Planning", "module": "agents.planning", "port": 8100},
    {"name": "Backend Coder", "module": "agents.backend_coder", "port": 8105},
    {"name": "Frontend Coder", "module": "agents.frontend_coder", "port": 8106},
    {"name": "QA Tester", "module": "agents.qa_tester", "port": 8107},
]

def main():
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # Always use .venv in current directory
    venv_python = Path.cwd() / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        print(f"❌ .venv not found at: {venv_python}"); sys.exit(1)
    
    print(f"✅ Using Python: {venv_python}")
    procs = []
    
    for svc in SERVICES:
        cmd = [str(venv_python), "-m", "uvicorn", f"{svc['module']}:app", "--host", "0.0.0.0", "--port", str(svc["port"]), "--log-level", "info"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        procs.append((svc["name"], proc))
        
        def stream(name, p):
            while True:
                line = p.stdout.readline()
                if not line: break
                try: print(f"[{name}] {line.decode('utf-8', errors='replace').strip()}")
                except: pass
        threading.Thread(target=stream, args=(svc["name"], proc), daemon=True).start()
        time.sleep(1)
    
    print("All services started. Press Ctrl+C to stop.\n" + "-"*60)
    try:
        while all(p.poll() is None for _, p in procs): time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping..."); [p.terminate() for _, p in procs]; [p.wait(timeout=3) for _, p in procs]

if __name__ == "__main__": main()
# TODO: Implement main
#!/usr/bin/env python3
import os, sys, json, re, asyncio, logging, httpx  # ← ADD httpx HERE
from pathlib import Path
from datetime import datetime
from core.config import settings
from core.state import StateManager
from core.context import ContextManager
from core.clients import ServiceClient, MCPFileWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def parse_qa_summary(text: str) -> dict:
    """Parse QA output into structured summary. Handles JSON or plain text."""
    import re
    
    # If already a dict, return as-is
    if isinstance(text, dict):
        return text
    
    text = str(text).strip()
    
    # Try to extract JSON from markdown
    try:
        # Look for JSON object in the text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            json_str = json_match.group(0)
            summary = json.loads(json_str)
            
            # Ensure bugs_found is list of dicts
            if "bugs_found" in summary:
                bugs = summary["bugs_found"]
                if isinstance(bugs, list):
                    # Convert string bugs to dict format
                    summary["bugs_found"] = [
                        {"description": str(b) if isinstance(b, str) else b.get("description", str(b))}
                        for b in bugs
                    ]
                else:
                    summary["bugs_found"] = []
            else:
                summary["bugs_found"] = []
                
            return summary
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ QA JSON parse failed: {e}")
    
    # Fallback: treat entire output as bug description
    return {
        "status": "fail",
        "bugs_found": [{"description": text[:500]}],  # First 500 chars
        "suggested_fixes": ["Review QA output manually"]
    }

async def run_orchestrator():
    logger.info("🚀 Starting SpecForge Orchestrator")
    sm = StateManager()
    ctx = ContextManager()
    client = ServiceClient()
    fs = MCPFileWriter(settings.output_dir)

    # Resume or Fresh Start
    state = sm.load()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(settings.output_dir) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if state and input(f"🔄 Resume from '{state['last_step']}'? (y/n): ").lower() == "y":
        completed = state["completed_steps"]
        tasks = state["tasks"]
        task_idx = state["task_index"]
        ctx.set(ctx.load() or "")
    else:
        idea = input("💡 Enter your project idea: ").strip()
        if not idea: raise ValueError("Idea cannot be empty")
        ctx.append(idea, "User Idea")
        completed, tasks, task_idx = set(), None, 0
        sm.clear()

    steps = [
        ("researcher", "planning"),
        ("ba", "planning"),
        ("architect", "planning"),
        ("pm", "planning")
    ]

    # ============================================================
    # Phase 1: Fixed Steps (researcher → ba → architect → pm)
    # ============================================================
    
    # Helper: async summarizer function (lambdas can't be async)
    async def _call_summarizer(combined_context: str, source_label: str) -> str:
        return await client.call(
            "planning",
            combined_context,
            instruction=f"Summarize as {source_label}",
            model=settings.summarizer_model,
            task_type="summarizer"  # ← Critical: planning service requires this
        )
    
    for step_name, svc in steps:
        if step_name in completed:
            logger.info(f"⏭️ Skipping completed: {step_name}")
            continue
            
        logger.info(f"🔍 Running: {step_name}")
        try:
            # Build instruction
            instruction_text = f"Process current context for {step_name}"
            
            # Call service: planning needs task_type, others don't
            if svc == "planning":
                res = await client.call(
                    svc,
                    ctx.get(),
                    instruction=instruction_text,
                    task_type=step_name  # ← Critical fix
                )
            else:
                res = await client.call(
                    svc,
                    ctx.get(),
                    instruction=instruction_text
                )
            
            # Save raw output
            raw_path = out_dir / f"{step_name}_raw.md"
            raw_path.write_text(res, encoding="utf-8")
            logger.debug(f"💾 Saved: {raw_path}")
            
            # Summarize and update context
            await ctx.summarize_and_replace(res, step_name, _call_summarizer)
            ctx.save()
            
            # Update state
            completed.add(step_name)
            sm.save(step_name, completed, tasks, task_idx)
            logger.info(f"✅ Completed: {step_name}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                logger.error(f"❌ {step_name} failed: 422 Unprocessable Entity")
                logger.error(f"   Response: {e.response.text[:300]}")
                logger.error(f"   This usually means missing 'task_type' for planning service")
            else:
                logger.error(f"❌ {step_name} failed: HTTP {e.response.status_code} - {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ {step_name} failed: {type(e).__name__}: {e}")
            import traceback
            logger.debug(f"Traceback:\n{traceback.format_exc()}")
            sys.exit(1)

    # Phase 2: Parse PM Plan
    if "pm" in completed and tasks is None:
        pm_out = Path(out_dir / "pm_raw.md").read_text()
        m = re.search(r'\[[\s\S]*?\]', pm_out, re.DOTALL)
        try: tasks = json.loads(m.group(0)) if m else []
        except: logger.warning("⚠️ PM parse failed, using fallback"); tasks = [{"agent": "Principal Software Engineer", "description": "Build core features"}]
        sm.save("pm", completed, tasks, 0)

    # ============================================================
    # Phase 3: Dynamic Tasks
    # ============================================================
    role_map = {
        "principal software engineer": "backend",
        "ui/ux developer": "frontend",
        "qa automation engineer": "qa"
    }

    if tasks:
        for i, t in enumerate(tasks[task_idx:], task_idx):
            # Handle both dict (fresh run) and list/tuple (resumed from state)
            if isinstance(t, dict):
                role = t.get("agent", "").lower()
                desc = t.get("description", "")
            elif isinstance(t, (list, tuple)) and len(t) >= 2:
                role = str(t[0]).lower()
                desc = str(t[1])
            else:
                logger.warning(f"⏭️ Skipping malformed task: {t}")
                continue

            svc = role_map.get(role)
            if not svc:
                logger.warning(f"⏭️ Skipping unmapped agent: {role}")
                continue

            logger.info(f"🛠️ Task {i+1}: {role} - {desc[:50]}...")
            try:
                res = await client.call(svc, ctx.get(), instruction=desc)
                safe_role = role.replace(" ", "_").replace("/", "_").replace("\\", "_")
                task_file = Path(out_dir / f"task_{i+1}_{safe_role}.md")
                task_file.write_text(res, encoding="utf-8")

                # Extract & write code blocks
                blocks = re.findall(r'```(?:python|javascript|jsx|tsx|ts|css|html)?\n#?\s*([\w\./\-]+)\n(.*?)```', res, re.DOTALL)
                for path, code in blocks:
                    await fs.write_file(path, code.strip())
                
                async def _task_summarizer(combined_context: str, source_label: str) -> str:
                    return await client.call(
                        "planning",
                        combined_context,
                        instruction=f"Summarize task output as {source_label}",
                        model=settings.summarizer_model,
                        task_type="summarizer"
                    )
                ctx.save()
            except Exception as e:
                logger.error(f"❌ Task {i+1} failed: {e}")
                sm.save(f"task_{i+1}", completed, tasks, i)
                sys.exit(1)

    # Phase 4: QA Loop
    logger.info("🧪 Starting QA Loop (max 3 iterations)")
    for qa_iter in range(1, 4):
        qa_out = await client.call("qa", ctx.get(), instruction="Test generated code against acceptance criteria")
        Path(out_dir / f"qa_iteration_{qa_iter}.md").write_text(qa_out, encoding="utf-8")
        summary = parse_qa_summary(qa_out)
        if summary.get("status") == "pass" and not summary.get("bugs_found"):
            logger.info("✅ QA passed on iteration " + str(qa_iter))
            break
        logger.warning(f"⚠️ QA iteration {qa_iter}: {len(summary.get('bugs_found',[]))} bugs found")
        if qa_iter < 3:
            bug_ctx = "\n".join([f"- {b.get('description','')}" for b in summary.get("bugs_found",[])])
            await client.call("backend", ctx.get(), instruction=f"Fix these QA bugs:\n{bug_ctx}")

    # Phase 5: Final Summary
    logger.info("📄 Generating final documentation...")
    final = await client.call("planning", ctx.get(), instruction="Compile all outputs into a final README & project summary",task_type="summarizer" )
    (out_dir / "README.md").write_text(final, encoding="utf-8")
    sm.save("complete", completed | {"researcher","ba","architect","pm","tasks","qa"}, tasks, len(tasks))
    logger.info(f"🎉 Orchestration complete! Outputs saved to: {out_dir}")

if __name__ == "__main__":
    asyncio.run(run_orchestrator())
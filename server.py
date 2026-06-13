"""
GitAtlas — FastAPI Backend
Serves the HTML frontend and handles all AI agent API calls
"""
import sys, os, json, math, base64, io, datetime, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Serve main HTML ───────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    return {"status": "ok", "groq": has_groq}

# ── Analyze — SSE streaming ───────────────────────────────────────────────────
@app.get("/api/analyze")
async def analyze(url: str):
    """Stream analysis results as Server-Sent Events"""
    def generate():
        def send(event, data):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            from github_fetcher import fetch_repository
            from perception import run_perception_agent
            from reasoning import run_reasoning_agent
            from action import run_action_agent

            def ts():
                return datetime.datetime.now().strftime("%I:%M:%S %p")

            # ── Step 0: Fetch ──────────────────────────────────────────────
            yield send("step", {"step": 0, "status": "active", "msg": "Fetching repository..."})
            t0 = time.time()
            raw = fetch_repository(url)
            fetch_dur = round(time.time() - t0, 1)
            meta = raw.get("metadata", {})
            full_name = meta.get("full_name", url)
            total_files = raw.get("total_files", 0)
            sel = len(raw.get("files_content", {}))
            lang = meta.get("language", "Unknown")
            yield send("step", {"step": 0, "status": "done", "dur": fetch_dur})

            # ── Step 1: Perception ─────────────────────────────────────────
            yield send("step", {"step": 1, "status": "active", "msg": "Perception Agent reading files..."})
            yield send("agent_msg", {"agent": "Perception", "abbr": "PER", "model": "Llama 3.1 8B", "time": ts(),
                "text": f"Scanning <strong>{full_name}</strong> — found <strong>{total_files:,} files</strong>. Connecting to GitHub API..."})
            t1 = time.time()
            perception = run_perception_agent(raw)
            percep_dur = round(time.time() - t1, 1)
            fw = perception.get("frameworks_detected", [])
            fw_str = f"Frameworks: <strong>{', '.join(fw[:3])}</strong>. " if fw else ""
            yield send("agent_msg", {"agent": "Perception", "abbr": "PER", "model": "Llama 3.1 8B", "time": ts(),
                "text": f"Primary: <strong>{lang}</strong>. {fw_str}Selected top <strong>{sel} files</strong>. Passing to Reasoning Agent..."})
            yield send("step", {"step": 1, "status": "done", "dur": percep_dur})

            # ── Step 2: Reasoning ──────────────────────────────────────────
            yield send("step", {"step": 2, "status": "active", "msg": "Reasoning Agent analyzing architecture..."})
            yield send("agent_msg", {"agent": "Reasoning", "abbr": "RES", "model": "Llama 3.3 70B", "time": ts(),
                "text": f"Received <strong>{sel} files</strong>. Building dependency map, cross-referencing imports..."})
            t2 = time.time()
            analysis = run_reasoning_agent(perception)
            reason_dur = round(time.time() - t2, 1)
            arch_p = analysis.get("architecture_analysis", {}).get("pattern", "Unknown")
            arch_c = analysis.get("architecture_analysis", {}).get("confidence", 0)
            comp_l = analysis.get("complexity_score", {}).get("level", "Medium")
            comp_s = analysis.get("complexity_score", {}).get("score", 50)
            mods = analysis.get("module_map", [])
            yield send("agent_msg", {"agent": "Reasoning", "abbr": "RES", "model": "Llama 3.3 70B", "time": ts(),
                "text": f"Architecture: <strong>{arch_p} MVC ({arch_c}% conf)</strong>. Complexity: <strong>{comp_l} {comp_s}/100</strong>. <strong>{len(mods)} modules</strong> detected."})
            yield send("step", {"step": 2, "status": "done", "dur": reason_dur})

            # ── Step 3: Action ─────────────────────────────────────────────
            yield send("step", {"step": 3, "status": "active", "msg": "Action Agent generating recommendations..."})
            yield send("agent_msg", {"agent": "Action", "abbr": "ACT", "model": "Llama 3.3 70B", "time": ts(),
                "text": f"Got analysis. Generating <strong>5 improvements</strong> + modernization plan..."})
            t3 = time.time()
            action_data = run_action_agent(analysis)
            action_dur = round(time.time() - t3, 1)
            top_imp = action_data.get("improvements", [{}])[0].get("title", "improvements") if action_data.get("improvements") else "recommendations"
            qs = action_data.get("code_quality_insights", {}).get("overall_quality_score", 0)
            yield send("agent_msg", {"agent": "Action", "abbr": "ACT", "model": "Llama 3.3 70B", "time": ts(),
                "text": f"Done! Top priority: <strong>{top_imp}</strong>. Quality score: <strong>{qs}/100</strong>. Chat agent ready."})
            yield send("step", {"step": 3, "status": "done", "dur": action_dur})

            total = round(time.time() - t0, 1)

            # ── Build graph image ──────────────────────────────────────────
            graph_b64 = ""
            try:
                from graph_builder import parse_modules_from_analysis, build_dependency_graph
                mods_g, edges = parse_modules_from_analysis(analysis)
                crit_name = analysis.get("dependency_analysis", {}).get("critical_module", "")
                for m in mods_g:
                    if m.get("name", "").lower() == crit_name.lower():
                        m["critical"] = True
                buf = build_dependency_graph(mods_g, edges, full_name)
                graph_b64 = base64.b64encode(buf.read()).decode()
            except Exception as e:
                graph_b64 = ""

            yield send("done", {
                "raw": {
                    "metadata": meta,
                    "total_files": total_files,
                    "files_analyzed": sel,
                },
                "perception": {
                    "languages": perception.get("languages_detected", []),
                    "frameworks": perception.get("frameworks_detected", []),
                    "has_tests": perception.get("has_tests", False),
                    "has_docker": perception.get("has_docker", False),
                },
                "analysis": {
                    "project_overview": analysis.get("project_overview", {}),
                    "architecture_analysis": analysis.get("architecture_analysis", {}),
                    "module_map": analysis.get("module_map", []),
                    "dependency_analysis": analysis.get("dependency_analysis", {}),
                    "complexity_score": analysis.get("complexity_score", {}),
                    "architecture_summary": analysis.get("architecture_summary", ""),
                    "security_surface": analysis.get("security_surface", []),
                    "reasoning_trace": analysis.get("reasoning_trace", []),
                },
                "action": {
                    "improvements": action_data.get("improvements", []),
                    "modernization_plan": action_data.get("modernization_plan", {}),
                    "code_quality_insights": action_data.get("code_quality_insights", {}),
                    "onboarding_guide": action_data.get("onboarding_guide", []),
                },
                "graph_b64": graph_b64,
                "durations": {"fetch": fetch_dur, "perception": percep_dur, "reasoning": reason_dur, "action": action_dur, "total": total},
            })

        except ValueError as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
        except PermissionError as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e), 'hint': 'Add GITHUB_TOKEN to .env'})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': f'{type(e).__name__}: {str(e)}'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    question = body.get("question", "")
    context = body.get("context", {})
    try:
        from action import chat_with_repo
        reply = chat_with_repo(question, context)
        return {"reply": reply}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ── Generate Docs ─────────────────────────────────────────────────────────────
@app.post("/api/docs")
async def gen_docs(request: Request):
    body = await request.json()
    analysis = body.get("analysis", {})
    perception = body.get("perception", {})
    try:
        from action import generate_docs

        class FakePerception:
            pass

        class PerceptionWrapper(dict):
            def get(self, k, d=None):
                if k == "_raw":
                    return {"files_content": {}, "metadata": perception.get("metadata", {})}
                return super().get(k, d)

        wrapped = PerceptionWrapper(perception)
        docs = generate_docs(analysis, wrapped)
        return {"docs": docs}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ── Compare ───────────────────────────────────────────────────────────────────
@app.post("/api/compare")
async def compare_repo(request: Request):
    body = await request.json()
    url2 = body.get("url", "")
    try:
        from github_fetcher import fetch_repository
        from perception import run_perception_agent
        from reasoning import run_reasoning_agent
        raw2 = fetch_repository(url2)
        p2 = run_perception_agent(raw2)
        a2 = run_reasoning_agent(p2)
        return {
            "metadata": raw2.get("metadata", {}),
            "total_files": raw2.get("total_files", 0),
            "architecture": a2.get("architecture_analysis", {}),
            "complexity": a2.get("complexity_score", {}),
            "modules": len(a2.get("module_map", [])),
            "tech_stack": a2.get("project_overview", {}).get("tech_stack", []),
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print("\n  GitAtlas is running!")
    print("  Open: http://localhost:8000\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

# ── GitHub Copilot Agent (GitHub Models API) ──────────────────────────────────
@app.post("/api/copilot")
async def copilot_agent(request: Request):
    """GitHub Copilot in Action — uses GitHub Models API for eligibility"""
    body = await request.json()
    question = body.get("question", "")
    context = body.get("context", {})
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return JSONResponse({"error": "GITHUB_TOKEN required for Copilot Agent"}, status_code=400)
    
    import httpx
    analysis = context.get("analysis", {})
    overview = analysis.get("project_overview", {})
    arch = analysis.get("architecture_analysis", {})
    modules = analysis.get("module_map", [])
    
    system_msg = f"""You are GitHub Copilot acting as an expert code assistant with deep context about this repository.

Repository context:
- Tech Stack: {', '.join(str(t) for t in overview.get('tech_stack', []))}
- Architecture: {arch.get('pattern', 'Unknown')} ({arch.get('confidence', 0)}% confidence)
- Modules: {', '.join(m.get('name','') for m in modules)}
- Summary: {analysis.get('architecture_summary', '')}

You help developers understand code, suggest improvements, and write new features. 
Always reference specific files and modules. Provide code examples when relevant."""

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://models.inference.ai.azure.com/chat/completions",
                headers={"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.5,
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                return {"reply": reply, "model": "GitHub Copilot (gpt-4o-mini)", "via": "github_models"}
            else:
                # Fallback to Groq if GitHub Models unavailable
                from action import chat_with_repo
                reply = chat_with_repo(question, context)
                return {"reply": reply, "model": "Llama 3.3 70B (fallback)", "via": "groq_fallback"}
    except Exception as e:
        from action import chat_with_repo
        reply = chat_with_repo(question, context)
        return {"reply": reply, "model": "Llama 3.3 70B (fallback)", "via": "groq_fallback", "note": str(e)}


# ── PR Creation (Simulated) ────────────────────────────────────────────────────
@app.post("/api/pr")
async def generate_pr(request: Request):
    body = await request.json()
    action_data = body.get("action_data", {})
    try:
        from action import generate_pr_draft
        pr = generate_pr_draft(action_data)
        return pr
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


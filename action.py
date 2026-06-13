"""
Action Agent — RepoMind Agent 3
Model: Groq Llama3 70B (llama-3.3-70b-versatile) — different rate pool
Chat Agent: Mixtral 8x7B
"""
import os, json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

def run_action_agent(analysis: dict) -> dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    arch = analysis.get("architecture_analysis",{})
    modules = analysis.get("module_map",[])
    complexity = analysis.get("complexity_score",{})
    overview = analysis.get("project_overview",{})

    prompt = f"""You are the Action Agent in RepoMind. Generate expert recommendations.

ANALYSIS:
Architecture: {arch.get('pattern')} ({arch.get('confidence')}% confidence)
Modules: {', '.join(m.get('name','') for m in modules)}
Complexity: {complexity.get('level')} ({complexity.get('score')}/100)
Tech Stack: {', '.join(str(t) for t in overview.get('tech_stack',[]))}
Summary: {analysis.get('architecture_summary','')}

Return ONLY valid JSON (no markdown):
{{
  "improvements": [
    {{"id":1,"title":"title","problem":"specific problem","solution":"concrete steps","impact":"Critical","effort":"Medium","category":"Security"}}
  ],
  "modernization_plan": {{
    "current_state": {{"description":"current arch desc","pain_points":["p1","p2","p3"]}},
    "recommended_state": {{"description":"recommended arch","key_changes":["c1","c2","c3"]}},
    "migration_steps": [{{"step":1,"action":"what to do","effort":"2 weeks"}}],
    "services_breakdown": [{{"service_name":"Service","responsibility":"what","from_modules":["Module A"]}}]
  }},
  "code_quality_insights": {{
    "missing_practices": ["practice1","practice2"],
    "security_concerns": ["concern1"],
    "performance_bottlenecks": ["bottleneck1"],
    "overall_quality_score": 70
  }},
  "onboarding_guide": ["step1","step2","step3","step4","step5"],
  "auto_docs": {{
    "project_description": "one paragraph project description",
    "installation": "installation steps",
    "key_modules": [{{"name":"Module","description":"what it does","key_functions":["func1"]}}],
    "api_overview": "API overview if applicable",
    "quick_start": "quick start guide"
  }}
}}

Provide exactly 5 improvements (Critical first). Be specific to the actual tech stack."""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"system","content":"Senior architect. Return only valid JSON. No markdown. No preamble."},
                  {"role":"user","content":prompt}],
        temperature=0.3, max_tokens=4096,
    )
    text = resp.choices[0].message.content.strip()
    if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text: text = "\n".join(text.split("\n")[1:-1])

    try:
        data = json.loads(text)
    except:
        data = _fallback_actions(analysis)

    data["_analysis"] = analysis
    data["_model_used"] = "llama-3.3-70b-versatile"
    return data

def chat_with_repo(question: str, full_context: dict) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analysis = full_context.get("analysis", {})
    perception = full_context.get("perception_data", {})
    raw = perception.get("_raw", {})
    files = raw.get("files_content", {})

    ctx = [
        f"Repo: {analysis.get('project_overview',{}).get('tech_stack',[])}",
        f"Architecture: {analysis.get('architecture_analysis',{}).get('pattern')}",
        f"Summary: {analysis.get('architecture_summary','')}",
        f"Modules: {', '.join(m.get('name','') for m in analysis.get('module_map',[]))}",
        "\nKey Files:\n" + "\n".join(f"--- {p} ---\n{c[:600]}" for p,c in list(files.items())[:6])
    ]

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role":"system","content":f"You are RepoMind, a senior software architect who deeply analyzed this codebase.\n\n{''.join(ctx)}\n\nAnswer with specific file/module references. Be concise but thorough. Use markdown for code."},
                {"role":"user","content":question}
            ],
            temperature=0.5, max_tokens=1200,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Chat error: {str(e)}"

def generate_docs(analysis: dict, perception_data: dict) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    raw = perception_data.get("_raw", {})
    files = raw.get("files_content", {})
    metadata = raw.get("metadata", {})
    overview = analysis.get("project_overview", {})
    modules = analysis.get("module_map", [])

    file_ctx = "\n".join(f"=== {p} ===\n{c[:800]}" for p,c in list(files.items())[:8])

    prompt = f"""Generate comprehensive README documentation for this repository.

Project: {metadata.get('full_name','')}
Description: {metadata.get('description','')}
Tech Stack: {', '.join(str(t) for t in overview.get('tech_stack',[]))}
Architecture: {analysis.get('architecture_analysis',{}).get('pattern')}
Modules: {', '.join(m.get('name','') for m in modules)}

FILE CONTENTS:
{file_ctx}

Generate a complete, professional README.md with:
- Project title and description
- Features list
- Tech stack
- Installation instructions
- Usage guide
- Architecture overview
- Module descriptions
- Contributing guide

Use proper markdown formatting. Be specific based on actual code."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":"Technical writer. Generate clean, professional README documentation."},
                      {"role":"user","content":prompt}],
            temperature=0.3, max_tokens=2000,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"# {metadata.get('name','Repository')}\n\nDocumentation generation failed: {str(e)}"

def _fallback_actions(analysis):
    return {
        "improvements":[
            {"id":1,"title":"Add Comprehensive Tests","problem":"Missing test coverage makes refactoring risky.","solution":"Add pytest with 80%+ coverage target. Start with unit tests for core business logic.","impact":"Critical","effort":"High","category":"Testing"},
            {"id":2,"title":"Structured Error Handling","problem":"No centralized error handling makes debugging hard.","solution":"Add middleware for error catching, structured logging with levels, integrate Sentry.","impact":"High","effort":"Medium","category":"Code Quality"},
            {"id":3,"title":"API Documentation","problem":"No API docs slows developer onboarding.","solution":"Add OpenAPI/Swagger. Auto-generate from code with docstrings.","impact":"High","effort":"Low","category":"Documentation"},
            {"id":4,"title":"Containerization","problem":"Environment inconsistencies cause deployment issues.","solution":"Add Dockerfile and docker-compose.yml for consistent environments.","impact":"Medium","effort":"Medium","category":"DevOps"},
            {"id":5,"title":"Caching Layer","problem":"Repeated expensive operations waste resources.","solution":"Add Redis caching for frequently accessed data with proper TTL strategy.","impact":"Medium","effort":"Medium","category":"Performance"},
        ],
        "modernization_plan":{
            "current_state":{"description":"Monolithic architecture, all components tightly coupled.","pain_points":["Hard to scale independently","Single point of failure","Full redeploy for any change"]},
            "recommended_state":{"description":"Modular services with clear boundaries.","key_changes":["Extract services by domain","Add API gateway","Event-driven communication"]},
            "migration_steps":[{"step":1,"action":"Map service boundaries","effort":"1 week"},{"step":2,"action":"Extract first service","effort":"2 weeks"},{"step":3,"action":"Add inter-service comms","effort":"1 week"}],
            "services_breakdown":[{"service_name":"API Service","responsibility":"HTTP handling","from_modules":[]},{"service_name":"Business Service","responsibility":"Core logic","from_modules":[]},{"service_name":"Data Service","responsibility":"Storage","from_modules":[]}],
        },
        "code_quality_insights":{"missing_practices":["Tests","Type hints","API docs","Logging"],"security_concerns":["Input validation","Auth hardening"],"performance_bottlenecks":["No caching","Sync I/O"],"overall_quality_score":65},
        "onboarding_guide":["Start with README and main entry point.","Explore folder structure and core modules.","Read configuration files for environment setup.","Run locally following setup guide.","Check existing tests to understand expected behavior."],
        "auto_docs":{"project_description":"A software project.","installation":"pip install -r requirements.txt","key_modules":[],"api_overview":"N/A","quick_start":"See README."},
        "_fallback":True,
    }


def generate_pr_draft(analysis: dict, pr_type: str = "refactor") -> dict:
    """Generate a simulated PR draft based on top improvement recommendation.

    Enhancements:
    - Improved LLM prompt for a richer PR draft
    - Adds implementation_summary, affected_modules, testing_checklist, risk_assessment
    - Keeps existing API fields for backward compatibility
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    # Select improvements from either raw analysis or previously-annotated _analysis
    imps = analysis.get("_analysis", {}).get("improvements", []) if "_analysis" in analysis else analysis.get("improvements", [])
    top = imps[0] if imps else {"title": "Refactor", "solution": "Improve code structure", "problem": "General cleanup"}
    arch = analysis.get("_analysis", {}).get("architecture_analysis", {}) if "_analysis" in analysis else {}
    stack = analysis.get("_analysis", {}).get("project_overview", {}).get("tech_stack", []) if "_analysis" in analysis else []

    # Improved, explicit prompt guiding the model to produce a structured, professional PR draft.
    prompt = f"""
You are an expert developer and release manager. Produce a realistic GitHub Pull Request draft for the requested improvement.

Context:
- Project tech stack: {', '.join(str(s) for s in stack) or 'Unknown'}
- Architecture: {arch.get('pattern', 'Monolithic')}
- PR type: {pr_type}

Improvement to implement:
- Title: {top.get('title')}
- Problem: {top.get('problem') or 'Not provided'}
- Proposed solution: {top.get('solution')}

Return ONLY valid JSON (no markdown wrappers). Include these fields:
{{
  "pr_title": "concise PR title (<72 chars)",
  "pr_branch": "feature/kebab-case-branch-name",
  "pr_body": "Full PR description in markdown with ## sections: Summary, Implementation, Changes, Testing, Risk Assessment. 200-300 words.",
  "implementation_summary": "One-paragraph description of how the change is implemented",
  "affected_modules": ["module.path.one", "module.two"],
  "changed_files": [{{"file":"path/to/file.py","status":"modified","additions":10,"deletions":2,"description":"what changed and why"}}],
  "labels": ["enhancement","refactor"],
  "testing_checklist": ["unit tests added","integration tests run","manual smoke test"],
  "risk_assessment": {{"risk_level":"Low/Medium/High","notes":"short notes"}},
  "estimated_review_time": "~15 min"
}}

Be specific and reference likely modules or files where applicable. Keep output compact and valid JSON.
"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Expert developer. Return only valid JSON. No markdown."},
                      {"role": "user", "content": prompt}],
            temperature=0.4, max_tokens=1500,
        )
        text = resp.choices[0].message.content.strip()
        # strip common code-fence wrappers
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = "\n".join(text.split("\n")[1:-1])

        result = json.loads(text)

        # Ensure we have a clear pr_title; if model returned generic, synthesize a concise one
        if not result.get("pr_title") or len(result.get("pr_title","")) < 6:
            short = top.get('title','Improvement').lower().replace(' ','-')[:60]
            result["pr_title"] = f"{pr_type}: {short}"

        return result
    except Exception as e:
        # Fallback retains original shape and adds the new optional fields for compatibility
        return {
            "pr_title": f"fix: {top.get('title','Improvement')}",
            "pr_branch": "feature/automated-improvement",
            "pr_body": f"## Summary\n\nAddresses: **{top.get('title')}**\n\n## Problem\n\n{top.get('problem','')}\n\n## Solution\n\n{top.get('solution','')}\n\n## Testing\n\nManual testing completed.",
            "implementation_summary": top.get('solution','See PR body'),
            "affected_modules": [m.get('name') for m in analysis.get('module_map',[])][:5],
            "changed_files": [{"file": "src/main.py", "status": "modified", "additions": 30, "deletions": 5, "description": "Applied recommended fix"}],
            "labels": ["enhancement"],
            "testing_checklist": ["Run unit tests","Run linters","Manual smoke test"],
            "risk_assessment": {"risk_level": "Medium", "notes": "Requires careful validation of core modules."},
            "estimated_review_time": "~10 min",
            "_error": str(e)
        }


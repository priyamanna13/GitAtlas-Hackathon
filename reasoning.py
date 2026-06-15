"""
Reasoning Agent — GitAtlas Agent 2
Model: Groq Llama 3.3 70B Versatile
Role: Think and understand — deep and precise
"""
import os, json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

def run_reasoning_agent(perception_data: dict) -> dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    raw = perception_data.get("_raw", {})
    files_content = raw.get("files_content", {})
    file_ctx = "\n".join(f"=== {p} ===\n{c[:1500]}" for p,c in files_content.items())

    prompt = f"""You are the Reasoning Agent in GitAtlas. Perform deep architectural analysis.

PERCEPTION DATA:
Repo: {perception_data.get('repo_name')}
Languages: {', '.join(perception_data.get('languages_detected',[]))}
Frameworks: {', '.join(perception_data.get('frameworks_detected',[]))}
Databases: {', '.join(perception_data.get('databases_detected',[]))}
Type: {perception_data.get('project_type')}
Observations: {json.dumps(perception_data.get('key_observations',[]))}

FILE CONTENTS:
{file_ctx}

Return ONLY valid JSON (no markdown):
{{
  "project_overview": {{
    "what_it_does": "3 clear sentences",
    "tech_stack": ["Python","Flask"],
    "project_type": "Web Application",
    "target_audience": "who uses this"
  }},
  "architecture_analysis": {{
    "pattern": "Monolithic",
    "confidence": 85,
    "reasoning": "why this pattern was detected",
    "sub_patterns": []
  }},
  "module_map": [
    {{"name":"Module","purpose":"what it does","files":["f.py"],"lines_of_code_estimate":300,"criticality":"Critical","critical":false}}
  ],
  "dependency_analysis": {{
    "relationships": [{{"from":"A","to":"B","type":"imports"}}],
    "critical_module": "most critical module name",
    "critical_module_reason": "why",
    "circular_dependencies": [],
    "description": "plain English dependency description"
  }},
  "complexity_score": {{
    "level": "Medium",
    "score": 60,
    "reasoning": "explanation",
    "factors": ["f1","f2"]
  }},
  "architecture_summary": "Under 150 words. Plain English. No jargon. For a new developer.",
  "security_surface": [
    {{
      "title": "finding title",
      "severity": "Critical",
      "file": "path/to/file.py",
      "line_hint": "approx area or function name",
      "description": "specific description of the vulnerability or concern",
      "recommendation": "concrete fix"
    }}
  ],
  "reasoning_trace": [
    {{"step": 1, "agent_thought": "What I looked at first and why", "finding": "What I found"}},
    {{"step": 2, "agent_thought": "Next analysis step", "finding": "Finding"}},
    {{"step": 3, "agent_thought": "Dependency mapping", "finding": "Finding"}},
    {{"step": 4, "agent_thought": "Security surface scan", "finding": "Finding"}},
    {{"step": 5, "agent_thought": "Final synthesis", "finding": "Conclusion"}}
  ],
  "scalability_assessment": "brief assessment"
}}

For security_surface: identify REAL issues in the actual files — hardcoded secrets, missing auth, SQL injection risks, exposed env vars, missing input validation. Be specific with file names.
For reasoning_trace: show your actual thinking process — what you looked at, what patterns you spotted, how you connected dots."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":"Senior software architect. Return only valid JSON. No markdown. No preamble."},
                      {"role":"user","content":prompt}],
            temperature=0.2, max_tokens=4000,
        )
        text = resp.choices[0].message.content.strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text: text = "\n".join(text.split("\n")[1:-1])

        analysis = json.loads(text)
    except Exception as ge:
        print(f"[Groq] Warning: API call failed ({type(ge).__name__}: {str(ge)}). Falling back to mock analysis.")
        analysis = _fallback(perception_data)

    # Normalize security_surface — support both old (string) and new (object) format
    sec = analysis.get("security_surface", [])
    normalized_sec = []
    for item in sec:
        if isinstance(item, str):
            normalized_sec.append({"title": item, "severity": "Medium", "file": "", "line_hint": "", "description": item, "recommendation": "Review and address."})
        elif isinstance(item, dict):
            normalized_sec.append(item)
    analysis["security_surface"] = normalized_sec

    critical_name = analysis.get("dependency_analysis",{}).get("critical_module","")
    for mod in analysis.get("module_map",[]):
        if mod.get("name","").lower() == critical_name.lower():
            mod["critical"] = True

    analysis["_perception"] = perception_data
    analysis["_model_used"] = "llama-3.3-70b-versatile"
    return analysis

def _fallback(p):
    langs = p.get("languages_detected",["Unknown"])
    return {
        "project_overview":{"what_it_does":f"A {p.get('project_type','app')} in {', '.join(langs)}.","tech_stack":langs,"project_type":p.get("project_type","App"),"target_audience":"Developers"},
        "architecture_analysis":{"pattern":"Monolithic","confidence":60,"reasoning":"Based on file structure.","sub_patterns":[]},
        "module_map":[
            {"name":"Core","purpose":"Main logic","files":p.get("entry_points",[]),"lines_of_code_estimate":500,"criticality":"Critical","critical":True},
            {"name":"Config","purpose":"Configuration","files":p.get("key_config_files",[]),"lines_of_code_estimate":100,"criticality":"High","critical":False},
            {"name":"Utils","purpose":"Helpers","files":[],"lines_of_code_estimate":150,"criticality":"Medium","critical":False},
        ],
        "dependency_analysis":{"relationships":[{"from":"Core","to":"Config","type":"imports"}],"critical_module":"Core","critical_module_reason":"Entry point","circular_dependencies":[],"description":"Core depends on Config and Utils."},
        "complexity_score":{"level":"Medium","score":50,"reasoning":"Standard complexity.","factors":["Multiple modules","External deps"]},
        "architecture_summary":f"A {p.get('project_type','application')} in {', '.join(langs[:2])}. Standard modular structure.",
        "security_surface":[{"title":"Input validation missing","severity":"High","file":"","line_hint":"","description":"No input validation detected on API endpoints.","recommendation":"Add schema validation (Pydantic/Zod)."}],
        "reasoning_trace":[
            {"step":1,"agent_thought":"Scanned entry points and folder structure","finding":"Identified primary language and project type"},
            {"step":2,"agent_thought":"Analyzed import graphs across files","finding":"Mapped module dependencies"},
            {"step":3,"agent_thought":"Checked for auth patterns and security primitives","finding":"Noted missing validation layer"},
            {"step":4,"agent_thought":"Estimated code complexity from file count and patterns","finding":"Medium complexity score"},
            {"step":5,"agent_thought":"Synthesized all findings into architecture pattern","finding":"Monolithic pattern with standard structure"},
        ],
        "scalability_assessment":"Standard deployment.","_fallback":True,
    }

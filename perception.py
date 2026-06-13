"""
Perception Agent — RepoMind Agent 1
Model: Groq Llama 3.1 8B Instant
Role: Read and extract — fast and wide
"""
import os, json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

def run_perception_agent(raw_repo_data: dict) -> dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    metadata = raw_repo_data.get("metadata", {})
    folder_structure = raw_repo_data.get("folder_structure", "")
    all_paths = raw_repo_data.get("all_paths_sample", [])
    files_content = raw_repo_data.get("files_content", {})

    files_summary = []
    for path, content in files_content.items():
        files_summary.append(f"--- FILE: {path} ---\n{content[:400]}\n")
    files_text = "\n".join(files_summary[:15])

    prompt = f"""You are the Perception Agent in RepoMind. Analyze this GitHub repository.

REPOSITORY: {metadata.get('full_name', 'Unknown')}
DESCRIPTION: {metadata.get('description', 'None')}
PRIMARY LANGUAGE: {metadata.get('language', 'Unknown')}
TOTAL FILES: {raw_repo_data.get('total_files', 0)}

FOLDER STRUCTURE:
{folder_structure}

FILE PATHS SAMPLE:
{chr(10).join(all_paths[:60])}

KEY FILE CONTENTS:
{files_text}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "repo_name": "name",
  "languages_detected": ["Python"],
  "frameworks_detected": ["Flask"],
  "databases_detected": [],
  "project_type": "Web Application",
  "entry_points": ["app.py"],
  "key_config_files": ["config.py"],
  "folder_structure_summary": "2-3 sentences",
  "has_tests": false,
  "has_docker": false,
  "has_ci_cd": false,
  "dependency_files": ["requirements.txt"],
  "total_selected_files": {len(files_content)},
  "key_observations": ["obs1","obs2","obs3","obs4","obs5"]
}}"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"system","content":"Senior engineer. Return only valid JSON. No markdown."},
                  {"role":"user","content":prompt}],
        temperature=0.1, max_tokens=1500,
    )
    text = resp.choices[0].message.content.strip()
    if "```json" in text: text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text: text = "\n".join(text.split("\n")[1:-1])

    try:
        data = json.loads(text)
    except:
        data = {
            "repo_name": metadata.get("name", "Unknown"),
            "languages_detected": [metadata.get("language","Unknown")],
            "frameworks_detected": [], "databases_detected": [],
            "project_type": "Web Application",
            "entry_points": list(files_content.keys())[:3],
            "key_config_files": [], "folder_structure_summary": folder_structure[:150],
            "has_tests": any("test" in p.lower() for p in all_paths),
            "has_docker": any("docker" in p.lower() for p in all_paths),
            "has_ci_cd": any(".github" in p.lower() for p in all_paths),
            "dependency_files": [], "total_selected_files": len(files_content),
            "key_observations": ["Analysis completed."], "_parse_error": True,
        }
    data["_raw"] = raw_repo_data
    data["_model_used"] = "llama-3.1-8b-instant"
    return data

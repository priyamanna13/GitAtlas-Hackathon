"""
Azure AI Foundry Reasoning Agent — GitAtlas
Model: Microsoft Phi-4-mini-reasoning (deployed on Azure AI Foundry)
SDK:   azure-ai-projects==2.2.0  (latest stable, May 2026)
Role:  Deep chain-of-thought reasoning over the Groq analysis results.
       Produces an enriched reasoning trace + security re-evaluation
       using Phi-4's multi-step <think>...</think> output.

Authentication:
  - DefaultAzureCredential: works with `az login` locally,
    Managed Identity on Azure, or Service Principal via env vars.
  - FOUNDRY_PROJECT_ENDPOINT: required env var
    Format: https://<service>.services.ai.azure.com/api/projects/<project>
  - MODEL_DEPLOYMENT_NAME: defaults to "phi-4-mini-reasoning"

Environment variables (add to .env):
  FOUNDRY_PROJECT_ENDPOINT=https://<your-service>.services.ai.azure.com/api/projects/<your-project>
  MODEL_DEPLOYMENT_NAME=phi-4-mini-reasoning        # optional, this is the default
"""

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "phi-4-mini-reasoning")
_MAX_TOKENS = 8192   # must be large enough to hold <think> trace + answer
_TEMPERATURE = 0.0   # deterministic for reproducible reasoning


def _is_foundry_configured() -> bool:
    """Return True only when the Foundry endpoint is set in the environment."""
    return bool(FOUNDRY_ENDPOINT and FOUNDRY_ENDPOINT.strip())


def _build_reasoning_prompt(groq_analysis: dict, perception_data: dict) -> str:
    """
    Build the prompt that Phi-4-mini-reasoning will reason over.
    We feed the Groq analysis as ground truth and ask Phi-4 to:
      1. Validate / challenge the architecture pattern conclusion
      2. Re-examine security findings with step-by-step reasoning
      3. Produce a ranked risk list with confidence scores
      4. Provide a 'reasoning_verdict' that agrees or corrects Groq's output
    """
    arch = groq_analysis.get("architecture_analysis", {})
    overview = groq_analysis.get("project_overview", {})
    modules = groq_analysis.get("module_map", [])
    security = groq_analysis.get("security_surface", [])
    complexity = groq_analysis.get("complexity_score", {})
    summary = groq_analysis.get("architecture_summary", "")

    raw = perception_data.get("_raw", {})
    files_content = raw.get("files_content", {})
    # Send up to 6 files, capped at 1 200 chars each, to stay within context
    file_ctx = "\n".join(
        f"=== {p} ===\n{c[:1200]}" for p, c in list(files_content.items())[:6]
    )

    security_json = json.dumps(security, indent=2)
    modules_json = json.dumps(
        [{"name": m.get("name"), "purpose": m.get("purpose"), "criticality": m.get("criticality")} for m in modules],
        indent=2,
    )

    return f"""You are a senior software architect performing a second-opinion reasoning audit on a repository that has already been analyzed by another AI.

Your task is to:
1. Reason step-by-step over the existing analysis findings
2. Validate or challenge the architecture pattern conclusion with evidence from the file contents
3. Re-examine each security finding and assign a concrete severity with reasoning
4. Produce a ranked risk assessment with confidence scores (0-100)
5. Give an overall reasoning verdict

EXISTING ANALYSIS (from primary agent):
- Repository: {groq_analysis.get("_perception", {}).get("repo_name", "Unknown")}
- Architecture Pattern: {arch.get("pattern", "Unknown")} ({arch.get("confidence", 0)}% confidence)
- Tech Stack: {", ".join(str(t) for t in overview.get("tech_stack", []))}
- Complexity: {complexity.get("level", "Unknown")} ({complexity.get("score", 0)}/100)
- Summary: {summary}

MODULES DETECTED:
{modules_json}

SECURITY FINDINGS (to re-evaluate):
{security_json}

KEY FILE CONTENTS (actual source):
{file_ctx}

Think carefully, step by step. Then return ONLY valid JSON (no markdown wrappers) in exactly this structure:
{{
  "architecture_verdict": {{
    "agrees_with_primary": true,
    "pattern_confirmed": "Monolithic",
    "confidence": 90,
    "reasoning": "Explain in 2-3 sentences why you agree or disagree, citing specific files."
  }},
  "security_reanalysis": [
    {{
      "title": "Finding title",
      "severity": "Critical",
      "confidence": 85,
      "file": "path/to/file.py",
      "phi4_reasoning": "Step-by-step reasoning for this finding",
      "recommendation": "Concrete fix"
    }}
  ],
  "risk_ranking": [
    {{"rank": 1, "risk": "Highest risk item", "severity": "Critical", "confidence": 90}},
    {{"rank": 2, "risk": "Second risk", "severity": "High", "confidence": 75}}
  ],
  "reasoning_verdict": "One paragraph. Overall assessment after re-examination. What the primary agent got right, what needs attention.",
  "phi4_chain_of_thought_summary": "2-3 sentence summary of the key reasoning steps Phi-4 took to reach these conclusions."
}}"""


def _parse_phi4_response(content: str) -> dict:
    """
    Parse Phi-4's response. The model outputs <think>...</think> followed by
    the JSON answer. Extract both the chain-of-thought and the JSON payload.
    """
    chain_of_thought = ""
    json_text = content

    # Extract <think> block if present
    if "<think>" in content and "</think>" in content:
        think_start = content.index("<think>") + len("<think>")
        think_end = content.index("</think>")
        chain_of_thought = content[think_start:think_end].strip()
        json_text = content[think_end + len("</think>"):].strip()

    # Strip any accidental markdown code fences
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif "```" in json_text:
        json_text = "\n".join(json_text.split("\n")[1:-1]).strip()

    # Attempt JSON parse
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        # Try to extract the first JSON object via regex
        match = re.search(r"\{.*\}", json_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

    parsed["_phi4_chain_of_thought"] = chain_of_thought
    return parsed


def run_azure_reasoning(groq_analysis: dict) -> dict:
    """
    Run Azure AI Foundry Phi-4-mini-reasoning over the Groq analysis.

    Returns an enrichment dict that gets merged back into the main analysis.
    If Foundry is not configured or unavailable, returns a safe fallback so
    the existing Groq pipeline is never broken.

    Args:
        groq_analysis: The dict returned by run_reasoning_agent() in reasoning.py

    Returns:
        dict with keys:
          - azure_reasoning: the full Phi-4 structured output
          - _azure_model_used: deployment name
          - _azure_status: "success" | "skipped" | "error"
          - _azure_error: error message if status == "error"
    """
    if not _is_foundry_configured():
        return {
            "azure_reasoning": None,
            "_azure_model_used": None,
            "_azure_status": "skipped",
            "_azure_error": (
                "FOUNDRY_PROJECT_ENDPOINT not set. "
                "Add it to .env to enable Azure AI Foundry reasoning."
            ),
        }

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as e:
        return {
            "azure_reasoning": None,
            "_azure_model_used": None,
            "_azure_status": "error",
            "_azure_error": (
                f"azure-ai-projects or azure-identity not installed: {e}. "
                "Run: pip install azure-ai-projects azure-identity"
            ),
        }

    perception_data = groq_analysis.get("_perception", {})
    prompt = _build_reasoning_prompt(groq_analysis, perception_data)

    try:
        with (
            DefaultAzureCredential() as credential,
            AIProjectClient(
                endpoint=FOUNDRY_ENDPOINT, credential=credential
            ) as project_client,
        ):
            # get_openai_client() returns a fully authenticated OpenAI-compatible
            # client that speaks to the project's model deployments — the
            # recommended pattern in azure-ai-projects >= 2.0.0
            oai_client = project_client.get_openai_client(api_version="2024-10-21")

            response = oai_client.chat.completions.create(
                model=DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a software architecture expert powered by Microsoft Phi-4. "
                            "Always reason step-by-step before giving your final JSON answer. "
                            "Return ONLY valid JSON — no markdown wrappers around the final answer."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                top_p=0.95,
            )

        full_content = response.choices[0].message.content or ""
        parsed = _parse_phi4_response(full_content)

        return {
            "azure_reasoning": parsed,
            "_azure_model_used": DEPLOYMENT_NAME,
            "_azure_status": "success",
            "_azure_token_usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }

    except Exception as e:
        return {
            "azure_reasoning": None,
            "_azure_model_used": DEPLOYMENT_NAME,
            "_azure_status": "error",
            "_azure_error": f"{type(e).__name__}: {str(e)}",
        }


def merge_azure_into_analysis(groq_analysis: dict, azure_result: dict) -> dict:
    """
    Merge the Azure Phi-4 reasoning enrichment back into the main analysis dict.

    The Groq analysis is the authoritative source. Azure enrichment:
      - Upgrades security_surface items with Phi-4's confidence scores and reasoning
      - Adds azure_reasoning block (architecture verdict, risk ranking, verdict)
      - Adds _azure_status so the UI can show whether Foundry ran

    Never removes or overwrites existing Groq fields.
    """
    azure_data = azure_result.get("azure_reasoning") or {}

    # Attach the raw Azure block (UI and health endpoint can read this)
    groq_analysis["azure_reasoning"] = azure_data
    groq_analysis["_azure_status"] = azure_result.get("_azure_status", "skipped")
    groq_analysis["_azure_model_used"] = azure_result.get("_azure_model_used")
    groq_analysis["_azure_error"] = azure_result.get("_azure_error")
    groq_analysis["_azure_token_usage"] = azure_result.get("_azure_token_usage")

    if not azure_data:
        return groq_analysis

    # Upgrade security_surface with Phi-4's re-analysis where titles match
    phi4_security = azure_data.get("security_reanalysis", [])
    if phi4_security:
        phi4_by_title = {s.get("title", "").lower(): s for s in phi4_security}
        for finding in groq_analysis.get("security_surface", []):
            match = phi4_by_title.get(finding.get("title", "").lower())
            if match:
                # Enrich with Phi-4's fields but keep all existing Groq fields
                finding["phi4_confidence"] = match.get("confidence")
                finding["phi4_reasoning"] = match.get("phi4_reasoning")
                # Upgrade severity if Phi-4 rates it higher
                severity_rank = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
                groq_sev = severity_rank.get(finding.get("severity", "Medium"), 2)
                phi4_sev = severity_rank.get(match.get("severity", "Medium"), 2)
                if phi4_sev > groq_sev:
                    finding["severity"] = match.get("severity")

    return groq_analysis

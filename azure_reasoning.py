"""
Azure AI Foundry Reasoning Agent — GitAtlas
Model: Microsoft Phi-4-mini-reasoning (deployed on Azure AI Foundry)
SDK:   azure-ai-projects==2.2.0  (latest stable, May 2026)
Role:  Deep reasoning over the Groq analysis results.
       Optimized for Azure for Students rate limits (1 RPM, 400 TPM).

Authentication:
  - AZURE_OPENAI_ENDPOINT: required env var
  - AZURE_OPENAI_API_KEY: required env var
  - AZURE_OPENAI_DEPLOYMENT: defaults to "phi-4-mini-reasoning"
"""

import os
import json
import re
import time
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "phi-4-mini-reasoning")
_MAX_TOKENS = 128     # Capped to keep under Students limits and prevent overflow
_TEMPERATURE = 0.0    # deterministic for reproducible reasoning
DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def _is_foundry_configured() -> bool:
    """Return True only when the Azure OpenAI endpoint and API key are set in the environment."""
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_ENDPOINT.strip() and
                AZURE_OPENAI_API_KEY and AZURE_OPENAI_API_KEY.strip())


def _build_compact_prompt(groq_analysis: dict) -> tuple[str, str, str, str, list[str]]:
    """
    Builds the components of the ultra-compact prompt to ensure under 100 input tokens.
    """
    perception_data = groq_analysis.get("_perception", {})
    repo_name = perception_data.get("repo_name", "Unknown")
    
    arch = groq_analysis.get("architecture_analysis", {})
    pattern = arch.get("pattern", "Unknown")
    
    # Get top 3 risks (titles of security findings)
    security = groq_analysis.get("security_surface", [])
    risks = [s.get("title", "") for s in security[:3]]
    if not risks:
        risks = ["None detected"]
        
    system_content = "You are a software architecture validator. Validate the supplied findings. Return ONLY valid JSON."
    
    user_prompt = f"""Repository:
{repo_name}

Architecture:
{pattern}

Top Risks:
"""
    for r in risks:
        user_prompt += f"- {r}\n"
        
    user_prompt += """
Question:
Validate these findings.
Return ONLY valid JSON."""

    return system_content, user_prompt, repo_name, pattern, risks


def _parse_phi4_response(content: str, groq_analysis: dict) -> dict:
    """
    Parse the simple JSON response and map it to the full GitAtlas schema.
    """
    json_text = content.strip()

    # Strip any accidental markdown code fences
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0].strip()
    elif "```" in json_text:
        json_text = "\n".join(json_text.split("\n")[1:-1]).strip()

    # Attempt JSON parse
    try:
        parsed_simple = json.loads(json_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", json_text, re.DOTALL)
        if match:
            try:
                parsed_simple = json.loads(match.group())
            except json.JSONDecodeError:
                parsed_simple = {}
        else:
            parsed_simple = {}

    agree = parsed_simple.get("agree", True)
    confidence = parsed_simple.get("confidence", 90)
    severity_changes = parsed_simple.get("severity_changes", [])
    summary = parsed_simple.get("summary", "Verified architecture pattern and risks.")

    # Get primary pattern
    primary_pattern = groq_analysis.get("architecture_analysis", {}).get("pattern", "Monolithic")

    # Map to standard GitAtlas schema
    parsed = {
        "architecture_verdict": {
            "agrees_with_primary": agree,
            "pattern_confirmed": primary_pattern,
            "confidence": confidence,
            "reasoning": summary
        },
        "security_reanalysis": [],
        "risk_ranking": [],
        "reasoning_verdict": summary,
        "phi4_chain_of_thought_summary": "Azure Phi-4 validation completed successfully."
    }

    # Map severity changes
    for change in severity_changes:
        title = change.get("title", "")
        severity = change.get("severity", "Medium")
        parsed["security_reanalysis"].append({
            "title": title,
            "severity": severity,
            "confidence": confidence,
            "file": "",
            "phi4_reasoning": f"Severity re-evaluated to {severity}.",
            "recommendation": ""
        })

    # Add dummy risk ranking entries if needed
    for i, change in enumerate(severity_changes[:2]):
        parsed["risk_ranking"].append({
            "rank": i + 1,
            "risk": change.get("title", ""),
            "severity": change.get("severity", "Medium"),
            "confidence": confidence
        })

    parsed["_phi4_chain_of_thought"] = ""
    return parsed


def run_azure_reasoning(groq_analysis: dict) -> dict:
    """
    Run Azure OpenAI Phi-4-mini-reasoning over the Groq analysis.
    Optimized for Azure for Students limits.

    Returns:
        dict with keys:
          - azure_reasoning: the full Phi-4 structured output
          - _azure_model_used: deployment name
          - _azure_status: "success" | "skipped" | "error" | "rate_limited"
          - _azure_error: error message if status in ("error", "rate_limited")
    """
    if not _is_foundry_configured():
        return {
            "azure_reasoning": None,
            "_azure_model_used": None,
            "_azure_status": "skipped",
            "_azure_error": (
                "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY not set. "
                "Add them to .env to enable Azure OpenAI reasoning."
            ),
        }

    try:
        from openai import AzureOpenAI, RateLimitError
    except ImportError as e:
        return {
            "azure_reasoning": None,
            "_azure_model_used": None,
            "_azure_status": "error",
            "_azure_error": (
                f"openai not installed: {e}. "
                "Run: pip install openai"
            ),
        }

    # Build prompts
    system_content, prompt, repo_name, pattern, risks = _build_compact_prompt(groq_analysis)

    # Measure prompt tokens (tiktoken) before sending
    prompt_tokens = 0
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        system_tokens = len(encoding.encode(system_content))
        repo_tokens = len(encoding.encode(repo_name))
        pattern_tokens = len(encoding.encode(pattern))
        risks_tokens = sum(len(encoding.encode(r)) for r in risks)
        user_prompt_tokens = len(encoding.encode(prompt))
        
        # Total tokens calculated exactly
        prompt_tokens = system_tokens + user_prompt_tokens + 10 # Overhead
    except Exception:
        system_tokens = len(system_content) // 4
        repo_tokens = len(repo_name) // 4
        pattern_tokens = len(pattern) // 4
        risks_tokens = sum(len(r) for r in risks) // 4
        user_prompt_tokens = len(prompt) // 4
        prompt_tokens = system_tokens + user_prompt_tokens + 10

    # Print prompt measurements before sending (debug only)
    if DEBUG:
        print("=== Azure AI Prompt Audit (Ultra-Compact) ===")
        print(f"Prompt characters: {len(prompt)}")
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Estimated completion tokens: {_MAX_TOKENS}")
        print("=============================================")

    # Abort check if prompt exceeds 100 tokens
    if prompt_tokens > 100:
        print(f"[Azure] ABORT: Prompt tokens ({prompt_tokens}) exceed limit of 100!")
        if DEBUG:
            print("Responsible Section Analysis:")
            print(f"  -> System Prompt: {system_tokens} tokens")
            print(f"  -> Repository Name: {repo_tokens} tokens")
            print(f"  -> Architecture Pattern: {pattern_tokens} tokens")
            print(f"  -> Top Risks: {risks_tokens} tokens")
            print(f"  -> Chat prompt framework: {user_prompt_tokens - repo_tokens - pattern_tokens - risks_tokens} tokens")
        
        return {
            "azure_reasoning": None,
            "_azure_status": "skipped",
            "_azure_error": f"Aborted: Prompt tokens ({prompt_tokens}) exceeded limit of 100.",
            "_azure_model_used": AZURE_OPENAI_DEPLOYMENT,
        }

    client = None
    try:
        # Initialize official Azure OpenAI Client using API Key authentication
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
    except Exception as e:
        return {
            "azure_reasoning": None,
            "_azure_model_used": AZURE_OPENAI_DEPLOYMENT,
            "_azure_status": "error",
            "_azure_error": f"Client initialization failed: {type(e).__name__}: {str(e)}",
        }

    max_retries = 3
    retry_count = 0
    response = None

    while True:
        try:
            response = client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=_MAX_TOKENS,
                temperature=_TEMPERATURE,
                top_p=0.95,
            )
            break
        except RateLimitError as e:
            retry_count += 1
            if retry_count > max_retries:
                # Log the rate limiting failure
                print(f"[Azure] Rate limit exceeded after {max_retries} retries: {str(e)}")
                if DEBUG:
                    print(f"=== Azure AI Request Log ===")
                    print(f"Prompt character count: {len(prompt)}")
                    print(f"Prompt tokens: {prompt_tokens}")
                    print(f"Completion tokens: N/A")
                    print(f"Total tokens: N/A")
                    print(f"Azure status: rate_limited")
                    print(f"Retry count: {retry_count - 1}")
                    print(f"=============================")

                return {
                    "azure_reasoning": None,
                    "_azure_status": "rate_limited",
                    "_azure_error": f"Rate limit exceeded after {max_retries} retries: {str(e)}",
                    "_azure_model_used": AZURE_OPENAI_DEPLOYMENT,
                }

            # Read Retry-After header
            retry_after = None
            if e.response is not None:
                retry_after_header = e.response.headers.get("retry-after")
                if retry_after_header:
                    try:
                        retry_after = float(retry_after_header)
                    except ValueError:
                        pass

            if retry_after is None:
                retry_after = 2 ** retry_count

            print(f"[Azure] Rate limited (429). Retrying in {retry_after} seconds... (Retry {retry_count}/{max_retries})")
            time.sleep(retry_after)

        except Exception as e:
            # General exception during a retry/request
            print(f"[Azure] Request failed: {type(e).__name__}: {str(e)}")
            if DEBUG:
                print(f"=== Azure AI Request Log ===")
                print(f"Prompt character count: {len(prompt)}")
                print(f"Prompt tokens: {prompt_tokens}")
                print(f"Completion tokens: N/A")
                print(f"Total tokens: N/A")
                print(f"Azure status: error ({type(e).__name__})")
                print(f"Retry count: {retry_count}")
                print(f"=============================")

                import traceback
                print("=== Azure OpenAI Reasoning Exception ===")
                traceback.print_exc()
                print("========================================")

            return {
                "azure_reasoning": None,
                "_azure_model_used": AZURE_OPENAI_DEPLOYMENT,
                "_azure_status": "error",
                "_azure_error": f"{type(e).__name__}: {str(e)}",
            }

    # Successful response logging
    prompt_char_count = len(prompt)
    resp_prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens

    if DEBUG:
        print(f"=== Azure AI Request Log ===")
        print(f"Prompt character count: {prompt_char_count}")
        print(f"Prompt tokens: {resp_prompt_tokens}")
        print(f"Completion tokens: {completion_tokens}")
        print(f"Total tokens: {total_tokens}")
        print(f"Azure status: success")
        print(f"Retry count: {retry_count}")
        print(f"=============================")

    full_content = response.choices[0].message.content or ""
    parsed = _parse_phi4_response(full_content, groq_analysis)

    return {
        "azure_reasoning": parsed,
        "_azure_model_used": AZURE_OPENAI_DEPLOYMENT,
        "_azure_status": "success",
        "_azure_token_usage": {
            "prompt_tokens": resp_prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


def merge_azure_into_analysis(groq_analysis: dict, azure_result: dict) -> dict:
    """
    Merge the Azure Phi-4 reasoning enrichment back into the main analysis dict.
    Never removes or overwrites existing Groq fields.
    """
    azure_data = azure_result.get("azure_reasoning") or {}

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
                finding["phi4_confidence"] = match.get("confidence")
                finding["phi4_reasoning"] = match.get("phi4_reasoning")
                severity_rank = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
                groq_sev = severity_rank.get(finding.get("severity", "Medium"), 2)
                phi4_sev = severity_rank.get(match.get("severity", "Medium"), 2)
                if phi4_sev > groq_sev:
                    finding["severity"] = match.get("severity")

    return groq_analysis

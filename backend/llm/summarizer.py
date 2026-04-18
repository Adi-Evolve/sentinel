"""Local LLM summarizer using Ollama.

This module provides offline LLM capabilities for generating
executive summaries and natural language explanations.
"""

from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)

# Default model - 3B parameters, runs on CPU
DEFAULT_MODEL = "llama3.2:3b"


def _get_llm(model: str = DEFAULT_MODEL, temperature: float = 0.7):
    """Initialize Ollama LLM client.
    
    Args:
        model: Name of the Ollama model to use
        temperature: Creativity level (0.0 = deterministic, 1.0 = creative)
        
    Returns:
        OllamaLLM instance or None if not available
    """
    try:
        from langchain_ollama import OllamaLLM
        
        llm = OllamaLLM(
            model=model,
            temperature=temperature,
            timeout=30,  # 30 second timeout
        )
        return llm
    except ImportError:
        LOGGER.warning("langchain-ollama not installed. LLM features disabled.")
        return None
    except Exception as e:
        LOGGER.error(f"Failed to initialize Ollama LLM: {e}")
        return None


def check_ollama_available() -> dict[str, Any]:
    """Check if Ollama is installed and running.
    
    Returns:
        Status dictionary with availability info
    """
    try:
        import subprocess
        
        # Check if ollama command exists
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse available models
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        models.append(parts[0])
            
            return {
                "available": True,
                "installed_models": models,
                "default_model": DEFAULT_MODEL,
                "default_model_ready": DEFAULT_MODEL in models,
            }
        else:
            return {
                "available": False,
                "error": "Ollama command failed",
                "installed_models": [],
                "default_model": DEFAULT_MODEL,
                "default_model_ready": False,
            }
            
    except FileNotFoundError:
        return {
            "available": False,
            "error": "Ollama not installed. Install from ollama.com",
            "installed_models": [],
            "default_model": DEFAULT_MODEL,
            "default_model_ready": False,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "installed_models": [],
            "default_model": DEFAULT_MODEL,
            "default_model_ready": False,
        }


def generate_executive_summary(scan_result: dict) -> dict[str, Any]:
    """Generate an executive summary of security scan results.
    
    Args:
        scan_result: Dictionary containing scan results with keys:
            - anomaly_count: int
            - top_anomaly: dict with rule_triggered, source_ip, severity_label
            - max_severity: str
            - total_events: int
            - scan_duration: float
            
    Returns:
        Dictionary with summary text and metadata
    """
    llm = _get_llm()
    
    if not llm:
        return {
            "summary": "LLM not available. Install Ollama and run: ollama pull llama3.2:3b",
            "generated_by": "fallback",
            "model": None,
            "error": "Ollama not configured",
        }
    
    # Extract key information
    anomaly_count = scan_result.get("anomaly_count", 0)
    top_anomaly = scan_result.get("anomalies", [{}])[0] if scan_result.get("anomalies") else {}
    
    rule_triggered = top_anomaly.get("rule_triggered", "unknown") if top_anomaly else "none"
    source_ip = top_anomaly.get("source_ip", "unknown") if top_anomaly else "none"
    severity = top_anomaly.get("severity_label", "unknown") if top_anomaly else "none"
    score = top_anomaly.get("composite_score", 0) if top_anomaly else 0
    total_events = scan_result.get("total_events", 0)
    
    # Build prompt
    prompt = f"""You are a Chief Information Security Officer (CISO) writing an executive summary.

SECURITY SCAN RESULTS:
- Total log events analyzed: {total_events:,}
- Threats detected: {anomaly_count}
- Highest severity: {severity}
- Top threat type: {rule_triggered}
- Source IP: {source_ip}
- Risk score: {score}/100

Write a 2-3 sentence executive summary for leadership. Be concise, professional, and actionable. Focus on business impact and required actions. Do not use technical jargon.

Executive Summary:"""

    try:
        LOGGER.info("Generating executive summary with Ollama...")
        summary = llm.invoke(prompt)
        
        return {
            "summary": summary.strip(),
            "generated_by": "ollama",
            "model": DEFAULT_MODEL,
            "prompt_tokens": len(prompt.split()),
            "local": True,
            "error": None,
        }
        
    except Exception as e:
        LOGGER.error(f"Failed to generate summary: {e}")
        return {
            "summary": f"Scan detected {anomaly_count} potential threats with maximum severity '{severity}'. "
                      f"Top threat from {source_ip} classified as {rule_triggered}. "
                      f"Immediate review recommended for high-risk anomalies.",
            "generated_by": "rule-based-fallback",
            "model": None,
            "error": str(e),
        }


def explain_threat_in_natural_language(anomaly: dict) -> dict[str, Any]:
    """Generate a natural language explanation of a specific threat.
    
    Args:
        anomaly: Dictionary containing anomaly details
        
    Returns:
        Dictionary with explanation and metadata
    """
    llm = _get_llm(temperature=0.5)  # More factual for explanations
    
    if not llm:
        return {
            "explanation": "LLM not available. Using rule-based explanation only.",
            "generated_by": "fallback",
            "model": None,
            "error": "Ollama not configured",
        }
    
    # Extract information
    rule = anomaly.get("rule_triggered", "unknown")
    ip = anomaly.get("source_ip", "unknown")
    country = anomaly.get("country_code", "unknown")
    score = anomaly.get("composite_score", 0)
    brief = anomaly.get("briefing", "No briefing available")
    
    # Get feature contributions if available
    explanation = anomaly.get("metadata", {}).get("model_explanation", {})
    features = explanation.get("feature_contributions", [])
    top_features = features[:3] if features else []
    
    feature_text = ""
    if top_features:
        feature_text = "Key indicators: " + ", ".join([
            f"{f['feature']} ({f['weight']:.1%})" for f in top_features
        ])
    
    prompt = f"""You are a security analyst explaining a threat to a non-technical manager.

THREAT DETAILS:
- Type: {rule}
- Source IP: {ip} ({country})
- Risk Score: {score}/100
- {feature_text}

Write a clear, non-technical explanation (2-3 sentences) of:
1. What happened
2. Why it's concerning
3. What action to take

Avoid jargon. Be specific but simple.

Explanation:"""

    try:
        explanation_text = llm.invoke(prompt)
        
        return {
            "explanation": explanation_text.strip(),
            "generated_by": "ollama",
            "model": DEFAULT_MODEL,
            "local": True,
            "error": None,
        }
        
    except Exception as e:
        LOGGER.error(f"Failed to generate explanation: {e}")
        return {
            "explanation": brief[:200] if brief else "Threat detected. Review recommended.",
            "generated_by": "briefing-fallback",
            "model": None,
            "error": str(e),
        }


def narrate_attack_chain(anomalies: list[dict]) -> dict[str, Any]:
    """Create a narrative story from multiple related anomalies.
    
    Args:
        anomalies: List of anomaly dictionaries in chronological order
        
    Returns:
        Dictionary with narrative and metadata
    """
    if len(anomalies) < 2:
        return {
            "narrative": "Single event detected. No attack chain to analyze.",
            "generated_by": "n/a",
            "model": None,
            "events_connected": 1,
        }
    
    llm = _get_llm(temperature=0.6)
    
    if not llm:
        return {
            "narrative": "Multiple suspicious events detected. Timeline analysis recommended.",
            "generated_by": "fallback",
            "model": None,
            "events_connected": len(anomalies),
            "error": "Ollama not configured",
        }
    
    # Build timeline summary
    events = []
    for i, a in enumerate(anomalies[:5], 1):  # Limit to 5 events
        time = a.get("timestamp", "unknown")
        rule = a.get("rule_triggered", "unknown")
        ip = a.get("source_ip", "unknown")
        events.append(f"{i}. [{time}] {rule} from {ip}")
    
    events_text = "\n".join(events)
    
    prompt = f"""You are a forensic analyst reconstructing an attack timeline.

SECURITY EVENTS (chronological):
{events_text}

Write a short narrative (3-4 sentences) connecting these events into a coherent attack chain. 
What might the attacker be trying to do? What's their likely next step?

Attack Narrative:"""

    try:
        narrative = llm.invoke(prompt)
        
        return {
            "narrative": narrative.strip(),
            "generated_by": "ollama",
            "model": DEFAULT_MODEL,
            "events_connected": len(anomalies),
            "local": True,
            "error": None,
        }
        
    except Exception as e:
        LOGGER.error(f"Failed to generate narrative: {e}")
        return {
            "narrative": f"Attack chain with {len(anomalies)} connected events detected. Review timeline for progression patterns.",
            "generated_by": "fallback",
            "model": None,
            "events_connected": len(anomalies),
            "error": str(e),
        }

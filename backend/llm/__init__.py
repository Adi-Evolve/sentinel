"""Local LLM integration module for Log-Sentinel.

Provides offline LLM capabilities using Ollama for:
- Executive summary generation
- Natural language threat explanations
- Attack chain narration
"""

from .summarizer import generate_executive_summary, explain_threat_in_natural_language

__all__ = ["generate_executive_summary", "explain_threat_in_natural_language"]

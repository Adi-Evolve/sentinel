"""Natural Language Query Engine - Chat with your logs using AI.

Allows users to ask questions about their log data in plain English:
- "Show me all failed logins from Russia"
- "What was the most active IP yesterday?"
- "Did we have any SQL injection attempts?"
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a natural language query."""
    query: str
    interpretation: str
    results: list[dict]
    summary: str
    sql_equivalent: Optional[str] = None


class NaturalLanguageQueryEngine:
    """AI-powered natural language query engine for log analysis."""
    
    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self._llm_available = self._check_llm()
    
    def _check_llm(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def _generate_query_plan(self, user_query: str, log_summary: dict) -> dict:
        """Use LLM to convert natural language to query plan."""
        if not self._llm_available:
            return self._fallback_query_plan(user_query)
        
        try:
            import requests
            
            prompt = f"""You are a log analysis AI assistant. Convert the user's question into a structured query plan.

Log Data Summary:
- Total events: {log_summary.get('total_events', 0)}
- Time range: {log_summary.get('time_range', 'unknown')}
- Unique IPs: {log_summary.get('unique_ips', 0)}
- Anomalies detected: {log_summary.get('anomaly_count', 0)}

User Question: "{user_query}"

Return a JSON object with:
- "intent": The query intent (filter, aggregate, compare, time_series, anomaly_search)
- "filters": Object with conditions like {{"ip": "1.2.3.4", "status": "failed", "country": "Russia"}}
- "time_range": Time window if specified (today, yesterday, last_hour, all)
- "group_by": Field to group results by (ip, country, time, status)
- "sort_by": How to sort results (count, time, severity)
- "limit": Max results to return

JSON response only:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1}
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                plan = json.loads(result.get("response", "{}"))
                return plan
                
        except Exception as e:
            logger.warning(f"LLM query planning failed: {e}")
        
        return self._fallback_query_plan(user_query)
    
    def _fallback_query_plan(self, user_query: str) -> dict:
        """Fallback query plan using keyword matching when LLM unavailable."""
        query_lower = user_query.lower()
        plan = {
            "intent": "filter",
            "filters": {},
            "time_range": "all",
            "group_by": None,
            "sort_by": "time",
            "limit": 50
        }
        
        # Extract IP addresses
        ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', user_query)
        if ip_match:
            plan["filters"]["ip"] = ip_match.group(0)
        
        # Detect failed/success patterns
        if any(word in query_lower for word in ['failed', 'failure', 'unsuccessful', 'denied', 'reject']):
            plan["filters"]["status"] = "failed"
        elif any(word in query_lower for word in ['success', 'successful', 'accepted', 'authenticated']):
            plan["filters"]["status"] = "success"
        
        # Detect time ranges
        if any(word in query_lower for word in ['today']):
            plan["time_range"] = "today"
        elif any(word in query_lower for word in ['yesterday']):
            plan["time_range"] = "yesterday"
        elif any(word in query_lower for word in ['hour', 'recent']):
            plan["time_range"] = "last_hour"
        
        # Detect grouping
        if any(word in query_lower for word in ['ip', 'address']):
            plan["group_by"] = "ip"
        elif any(word in query_lower for word in ['country', 'location']):
            plan["group_by"] = "country"
        elif any(word in query_lower for word in ['most active', 'top', 'highest']):
            plan["sort_by"] = "count"
            plan["limit"] = 10
        
        # Detect attack patterns
        if any(word in query_lower for word in ['brute force', 'brute-force', 'login attempt', 'password']):
            plan["filters"]["event_type"] = "failed_login"
        elif any(word in query_lower for word in ['sql', 'injection', 'sqli']):
            plan["filters"]["event_type"] = "attack"
            plan["filters"]["attack_type"] = "sql_injection"
        elif any(word in query_lower for word in ['xss', 'cross site']):
            plan["filters"]["event_type"] = "attack"
            plan["filters"]["attack_type"] = "xss"
        
        return plan
    
    def _execute_query_plan(self, plan: dict, events: list[dict]) -> list[dict]:
        """Execute query plan against event data."""
        results = events.copy()
        
        # Apply filters
        filters = plan.get("filters", {})
        if filters.get("ip"):
            results = [e for e in results if e.get("source_ip") == filters["ip"]]
        
        if filters.get("status") == "failed":
            results = [e for e in results if e.get("status_code", 200) >= 400 or 
                      "failed" in e.get("event_type", "").lower()]
        elif filters.get("status") == "success":
            results = [e for e in results if e.get("status_code", 200) < 400]
        
        if filters.get("event_type"):
            target = filters["event_type"].lower()
            results = [e for e in results if target in e.get("event_type", "").lower()]
        
        if filters.get("country"):
            target = filters["country"].lower()
            results = [e for e in results if target in e.get("country_code", "").lower() or
                      target in e.get("country_name", "").lower()]
        
        # Apply time range filtering (simplified)
        time_range = plan.get("time_range", "all")
        if time_range != "all":
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            
            if time_range == "today":
                cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == "yesterday":
                yesterday = now - timedelta(days=1)
                cutoff = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(hour=0, minute=0, second=0, microsecond=0)
                results = [e for e in results if cutoff <= datetime.fromisoformat(e.get("timestamp", "2020-01-01")) < end]
            elif time_range == "last_hour":
                cutoff = now - timedelta(hours=1)
                results = [e for e in results if datetime.fromisoformat(e.get("timestamp", "2020-01-01")) >= cutoff]
            
            if time_range == "today":
                results = [e for e in results if datetime.fromisoformat(e.get("timestamp", "2020-01-01")) >= cutoff]
        
        # Group results if needed
        group_by = plan.get("group_by")
        if group_by == "ip":
            from collections import Counter
            ip_counts = Counter(e.get("source_ip", "unknown") for e in results)
            results = [{"ip": ip, "count": count} for ip, count in ip_counts.most_common()]
        
        # Sort and limit
        sort_by = plan.get("sort_by", "time")
        limit = plan.get("limit", 50)
        
        if sort_by == "time":
            results = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
        elif sort_by == "count":
            results = sorted(results, key=lambda x: x.get("count", 0), reverse=True)
        
        return results[:limit]
    
    def _generate_summary(self, user_query: str, plan: dict, results: list[dict]) -> str:
        """Generate natural language summary of query results."""
        count = len(results)
        
        if not self._llm_available:
            return f"Found {count} events matching your query."
        
        try:
            import requests
            
            sample_results = json.dumps(results[:5], indent=2) if results else "No results"
            
            prompt = f"""Summarize these log query results in 1-2 sentences.

User Question: "{user_query}"
Results Count: {count}
Sample Results: {sample_results}

Provide a brief, natural language summary:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", f"Found {count} matching events.").strip()
                
        except Exception:
            pass
        
        return f"Found {count} events matching your query."
    
    def query(self, user_question: str, scan_data: dict) -> QueryResult:
        """Execute a natural language query against scan data.
        
        Args:
            user_question: Natural language question about logs
            scan_data: Complete scan result data including events
            
        Returns:
            QueryResult with interpretation, results, and summary
        """
        # Extract events from scan data
        events = scan_data.get("events_preview", [])
        if not events and scan_data.get("anomalies"):
            # Fallback to anomaly data if no raw events
            events = [
                {
                    "source_ip": a.get("source_ip"),
                    "timestamp": a.get("start_time"),
                    "event_type": a.get("type"),
                    "status_code": a.get("metadata", {}).get("status_code"),
                    "country_code": a.get("country_code"),
                }
                for a in scan_data.get("anomalies", [])
            ]
        
        # Build log summary
        log_summary = {
            "total_events": len(events),
            "time_range": scan_data.get("time_range", "unknown"),
            "unique_ips": len(set(e.get("source_ip") for e in events if e.get("source_ip"))),
            "anomaly_count": len(scan_data.get("anomalies", [])),
        }
        
        # Generate query plan
        plan = self._generate_query_plan(user_question, log_summary)
        
        # Execute query
        results = self._execute_query_plan(plan, events)
        
        # Generate summary
        summary = self._generate_summary(user_question, plan, results)
        
        # Build interpretation
        interpretation = f"""Interpreted as: {plan.get('intent', 'filter')} query
Filters: {json.dumps(plan.get('filters', {}))}
Time range: {plan.get('time_range', 'all')}"""
        
        return QueryResult(
            query=user_question,
            interpretation=interpretation,
            results=results,
            summary=summary,
        )


# Singleton instance
_query_engine: Optional[NaturalLanguageQueryEngine] = None


def get_query_engine() -> NaturalLanguageQueryEngine:
    """Get or create the query engine singleton."""
    global _query_engine
    if _query_engine is None:
        _query_engine = NaturalLanguageQueryEngine()
    return _query_engine


def query_logs(question: str, scan_data: dict) -> dict:
    """Public API for natural language log queries.
    
    Example:
        result = query_logs("Show failed logins from Russia", scan_data)
        # Returns: {"query": "...", "results": [...], "summary": "...", "interpretation": "..."}
    """
    engine = get_query_engine()
    result = engine.query(question, scan_data)
    
    return {
        "query": result.query,
        "interpretation": result.interpretation,
        "results": result.results,
        "summary": result.summary,
        "llm_available": engine._llm_available,
    }

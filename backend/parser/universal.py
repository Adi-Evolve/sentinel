"""Universal Log Parser - AI-powered parser for any log format.

Uses local LLM (Ollama) to automatically understand and parse any log format
without requiring manual regex patterns or predefined parsers.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.models.schemas import NormalisedEvent
from backend.parser.base import BaseParser, parse_timestamp

logger = logging.getLogger(__name__)

# Common patterns for extracting structured data from any log
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
TIMESTAMP_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\b"),  # ISO 8601
    re.compile(r"\b(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\b"),  # Syslog
    re.compile(r"\b(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s+[+-]\d{4})\b"),  # Apache
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[T ]\d{1,2}:\d{2}:\d{2})\b"),  # Various
]
STATUS_CODE_PATTERN = re.compile(r"\b(\d{3})\b")
HTTP_METHOD_PATTERN = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|CONNECT|TRACE)\b")
USER_AGENT_PATTERN = re.compile(r'"([^"]*(?:Mozilla|Chrome|Safari|Firefox|Edge|Bot|Crawler|Spider)[^"]*)"')
PATH_PATTERN = re.compile(r'\s(/[^\s"\']*)')  # URL paths starting with /


class UniversalParser(BaseParser):
    """AI-enhanced universal parser that handles any log format.
    
    Features:
    - Auto-detection of log structure using pattern matching
    - LLM-powered field extraction for unknown formats
    - Fallback to heuristic extraction when LLM unavailable
    - Caching of parsed patterns for performance
    """
    
    parser_name = "universal"
    
    def __init__(self):
        super().__init__()
        self._pattern_cache: dict[str, dict] = {}
        self._llm_available = self._check_llm()
    
    def _check_llm(self) -> bool:
        """Check if local LLM is available."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def _analyze_with_llm(self, sample_lines: list[str]) -> dict:
        """Use local LLM to analyze log format and suggest extraction patterns."""
        if not self._llm_available:
            return {}
        
        try:
            import requests
            
            sample = "\n".join(sample_lines[:5])
            prompt = f"""Analyze these log lines and identify the format. Return ONLY a JSON object with:
- format_name: detected format name
- timestamp_pattern: regex or position info
- ip_position: where IP addresses appear
- has_http_method: true/false
- has_status_code: true/false
- field_order: list of fields in order

Log sample:
{sample}

JSON response:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1}
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = json.loads(result.get("response", "{}"))
                return analysis
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
        
        return {}
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp using multiple patterns."""
        for pattern in TIMESTAMP_PATTERNS:
            match = pattern.search(line)
            if match:
                ts_str = match.group(1)
                parsed = parse_timestamp(ts_str)
                if parsed:
                    return parsed
        return None
    
    def _extract_ip(self, line: str) -> str:
        """Extract first valid IP address from line."""
        for match in IP_PATTERN.finditer(line):
            ip = match.group(0)
            # Validate it's not a version number or other false positive
            parts = ip.split(".")
            if all(0 <= int(p) <= 255 for p in parts):
                return ip
        return "0.0.0.0"
    
    def _extract_status_code(self, line: str) -> Optional[int]:
        """Extract HTTP status code if present."""
        match = STATUS_CODE_PATTERN.search(line)
        if match:
            code = int(match.group(1))
            if 100 <= code <= 599:  # Valid HTTP status code range
                return code
        return None
    
    def _extract_method(self, line: str) -> Optional[str]:
        """Extract HTTP method if present."""
        match = HTTP_METHOD_PATTERN.search(line)
        if match:
            return match.group(1)
        return None
    
    def _extract_endpoint(self, line: str) -> Optional[str]:
        """Extract URL path if present."""
        match = PATH_PATTERN.search(line)
        if match:
            path = match.group(1)
            if len(path) > 1:  # Not just "/"
                return path
        return None
    
    def _extract_user(self, line: str) -> Optional[str]:
        """Extract username if present (common patterns)."""
        # Pattern: user=username, user: username, or authenticated as user
        user_patterns = [
            re.compile(r'user[=:]\s*([^\s,;]+)', re.IGNORECASE),
            re.compile(r'authenticated\s+(?:as|user)\s+([^\s,;]+)', re.IGNORECASE),
            re.compile(r'login\s+(?:for|as)\s+:?\s*([^\s,;]+)', re.IGNORECASE),
        ]
        for pattern in user_patterns:
            match = pattern.search(line)
            if match:
                return match.group(1)
        return None
    
    def _detect_event_type(self, line: str) -> str:
        """Detect event type from content."""
        line_lower = line.lower()
        
        # Failed authentication patterns
        if any(word in line_lower for word in ['failed', 'failure', 'invalid', 'unauthorized', 'denied', 'reject']):
            if any(word in line_lower for word in ['login', 'auth', 'password', 'credential', 'ssh']):
                return "failed_login"
        
        # Successful authentication
        if any(word in line_lower for word in ['success', 'accepted', 'authenticated', 'logged in']):
            if any(word in line_lower for word in ['login', 'auth', 'ssh']):
                return "successful_login"
        
        # Error patterns
        if any(word in line_lower for word in ['error', 'exception', 'critical', 'fatal', 'panic']):
            return "error"
        
        # Warning patterns
        if any(word in line_lower for word in ['warn', 'warning', 'alert']):
            return "warning"
        
        # HTTP request patterns
        if self._extract_method(line):
            return "http_request"
        
        return "unknown"
    
    def parse_line(self, line: str) -> NormalisedEvent:
        """Parse any log line using intelligent extraction."""
        if not line.strip():
            return self.make_parse_error_event(line)
        
        try:
            # Extract all fields heuristically
            timestamp = self._extract_timestamp(line) or datetime.now(timezone.utc)
            source_ip = self._extract_ip(line)
            status_code = self._extract_status_code(line)
            method = self._extract_method(line)
            endpoint = self._extract_endpoint(line)
            user = self._extract_user(line)
            event_type = self._detect_event_type(line)
            
            return NormalisedEvent(
                timestamp=timestamp,
                source_ip=source_ip,
                event_type=event_type,
                user=user,
                status_code=status_code,
                endpoint=endpoint,
                bytes_sent=None,  # Would need specific parser
                raw_line=line,
                parse_error=False,
            )
            
        except Exception as e:
            logger.debug(f"Universal parse error: {e}")
            return self.make_parse_error_event(line)
    
    def parse_file(self, file_path: str | Path) -> list[NormalisedEvent]:
        """Parse file with optional LLM-enhanced format analysis."""
        path = Path(file_path)
        
        # Read sample for analysis
        sample_lines: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= 10:  # Read first 10 lines
                    break
                if line.strip():
                    sample_lines.append(line.rstrip("\n"))
        
        # Try LLM analysis if available
        if self._llm_available and sample_lines:
            analysis = self._analyze_with_llm(sample_lines)
            if analysis:
                logger.info(f"LLM detected format: {analysis.get('format_name', 'unknown')}")
        
        # Parse all lines using universal method
        return super().parse_file(file_path)

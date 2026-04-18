from __future__ import annotations

import json
import logging
from pathlib import Path
import tempfile

from backend.config import SCAN_RESULTS_DIR


LOGGER = logging.getLogger(__name__)


class JsonScanResultStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else SCAN_RESULTS_DIR
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_result(self, payload: dict) -> Path:
        scan_id = str(payload.get("scan_id", "")).strip()
        if not scan_id:
            raise ValueError("scan_id is required to persist a scan result.")

        destination = self._path_for(scan_id)
        serialized = json.dumps(payload, indent=2, ensure_ascii=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.root_dir),
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(serialized)
                temp_path = Path(handle.name)
            temp_path.replace(destination)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
        return destination

    def get_result(self, scan_id: str) -> dict | None:
        candidate = self._path_for(scan_id)
        if not candidate.exists():
            return None
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            quarantine_dir = self.root_dir / "_corrupt"
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            quarantine_path = quarantine_dir / candidate.name
            try:
                candidate.replace(quarantine_path)
            except OSError:
                quarantine_path = candidate
            LOGGER.warning(
                "Corrupted scan result JSON encountered for scan_id=%s path=%s",
                scan_id,
                quarantine_path,
            )
            return None

    def list_scan_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root_dir.glob("*.json"))

    def count(self) -> int:
        return len(self.list_scan_ids())

    def load_all_results(self) -> dict[str, dict]:
        results: dict[str, dict] = {}
        for scan_id in self.list_scan_ids():
            payload = self.get_result(scan_id)
            if payload is not None:
                results[scan_id] = payload
        return results

    def list_scan_summaries(self) -> list[dict]:
        summaries: list[dict] = []
        for scan_id in self.list_scan_ids():
            payload = self.get_result(scan_id)
            if payload is None:
                continue
            anomalies = payload.get("anomalies", [])
            summaries.append(
                {
                    "scan_id": scan_id,
                    "scan_timestamp": payload.get("scan_timestamp"),
                    "filename": payload.get("filename"),
                    "detected_format": payload.get("detected_format"),
                    "total_events": payload.get("total_events", 0),
                    "unique_ips": payload.get("unique_ips", 0),
                    "anomaly_count": len(anomalies),
                    "top_score": max((float(item.get("composite_score", 0.0)) for item in anomalies), default=0.0),
                }
            )
        summaries.sort(key=lambda item: item.get("scan_timestamp") or "", reverse=True)
        return summaries

    def delete_result(self, scan_id: str) -> bool:
        candidate = self._path_for(scan_id)
        if not candidate.exists():
            return False
        candidate.unlink()
        return True

    def _path_for(self, scan_id: str) -> Path:
        safe_scan_id = "".join(char for char in scan_id if char.isalnum() or char in {"-", "_"})
        return self.root_dir / f"{safe_scan_id}.json"

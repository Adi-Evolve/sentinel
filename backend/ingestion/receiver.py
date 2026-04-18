from __future__ import annotations

import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.config import ALLOWED_EXTENSIONS, TEMP_DIR


def _normalise_filename(filename: str) -> str:
    cleaned = secure_filename(filename or "upload.log")
    return cleaned or "upload.log"


def _validate_extension(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {path.suffix or '<none>'}")


def save_uploaded_file(upload: FileStorage) -> tuple[Path, str]:
    if upload is None or not upload.filename:
        raise ValueError("No file uploaded.")

    filename = _normalise_filename(upload.filename)
    candidate = Path(filename)
    _validate_extension(candidate)

    upload.stream.seek(0, 2)
    size_bytes = upload.stream.tell()
    upload.stream.seek(0)
    if size_bytes == 0:
        raise ValueError("Uploaded file is empty.")

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = TEMP_DIR / f"{uuid.uuid4()}_{filename}"
    upload.save(temp_path)
    return temp_path, filename


def cleanup_temp_file(path: str | Path) -> None:
    temp_path = Path(path)
    if temp_path.exists():
        temp_path.unlink()

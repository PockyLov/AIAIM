from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def local_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def safe_timestamp_for_filename(timestamp: str) -> str:
    return (
        timestamp.replace(":", "")
        .replace("-", "")
        .replace(".", "")
        .replace("+", "_")
    )


def write_metadata(metadata: dict[str, Any], metadata_path: Path) -> Path:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata["metadata_path"] = str(metadata_path)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return metadata_path

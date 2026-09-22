import json
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
FILE = DATA_DIR / "vault.json"


def load() -> dict | None:
    try:
        return json.loads(FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save(creds: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(creds, f)
    os.replace(tmp, FILE)

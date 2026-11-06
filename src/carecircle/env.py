"""A tiny .env reader/writer, so secrets stay out of the repo and out of chat."""

from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path = Path(".env")) -> None:
    """Put KEY=value lines from `path` into os.environ, without overriding."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def set_env_values(path: Path, values: dict[str, str]) -> None:
    """Write or replace KEY=value lines in `path`, keeping everything else."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in remaining.items()]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    for k, v in values.items():
        os.environ[k] = v


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("paste-"):
        raise SystemExit(f"{name} is not set. Put it in the .env file (see .env.example).")
    return value

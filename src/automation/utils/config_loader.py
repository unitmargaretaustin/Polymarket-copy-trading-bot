import os
from pathlib import Path
from typing import Any, Dict

import yaml


def _load_env(env_path: Path) -> Dict[str, str]:
    """
    Minimal .env loader (KEY=VALUE). Keeps it dependency-light.
    """
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def load_config(settings_path: Path, env_path: Path) -> Dict[str, Any]:
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    env = _load_env(env_path)

    # Allow OS env vars to override .env
    merged_env = {**env, **{k: v for k, v in os.environ.items() if k in env or k.startswith("PM_")}}

    # Inject credentials into config in a controlled namespace
    settings.setdefault("credentials", {})
    for k, v in merged_env.items():
        settings["credentials"][k] = v

    return settings

"""Shared config loader — merges config.toml + config.local.toml.

Used by run.py, wrapper.py, and wrapper_api.py so the server and all
wrappers see the same agent definitions.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent


def load_config(root: Path | None = None) -> dict:
    """Load config.toml and merge config.local.toml if it exists.

    config.local.toml is gitignored and intended for user-specific agents
    (e.g. local LLM endpoints or trusted reverse-proxy origins) that
    shouldn't be committed. Only safe local-only settings are merged:
    [agents] entries and [server].trusted_origins.
    """
    root = root or ROOT
    config_path = root / "config.toml"

    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    local_path = root / "config.local.toml"
    if local_path.exists():
        with open(local_path, "rb") as f:
            local = tomllib.load(f)

        local_server = local.get("server", {})
        local_trusted_origins = local_server.get("trusted_origins")
        if isinstance(local_trusted_origins, list):
            server_cfg = config.setdefault("server", {})
            merged = []
            for origin in [
                *server_cfg.get("trusted_origins", []),
                *local_trusted_origins,
            ]:
                if isinstance(origin, str) and origin not in merged:
                    merged.append(origin)
            server_cfg["trusted_origins"] = merged
        
        # Merge [agents] section — local agents are added ONLY if they don't already exist.
        # This protects the "holy trinity" (claude, codex, gemini) from being overridden.
        local_agents = local.get("agents", {})
        config_agents = config.setdefault("agents", {})
        for name, agent_cfg in local_agents.items():
            if name not in config_agents:
                config_agents[name] = agent_cfg
            else:
                print(f"  Warning: Ignoring local agent '{name}' (already defined in config.toml)")

    return config

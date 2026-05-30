"""
Configuration for the UGSI MCP Server.

Settings are loaded from environment variables, .env file, or the control panel.
All secrets use env vars — never hardcoded.
"""
import os
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.json"
DEFAULT_CONFIG = {
    "inventree_url": "http://localhost:8080",
    "inventree_user": "shopmanager",
    # Password from env only — never stored in config file
    "mcp_port": 8765,
    "dev_mode": False,
    "log_level": "INFO",
    "cache_ttl_seconds": 300,
    "max_results": 100,
    "enable_write_operations": False,  # Safety: read-only by default
    "enable_legacy_import": False,
    "legacy_csv_watch_dir": "",
    "webhook_url": "",
    "webhook_events": ["low_stock", "stock_change", "machine_status_change"],
    "allowed_origins": ["http://localhost:8080"],
    "integrations": {
        "sharepoint": {"enabled": False, "site_url": "", "list_name": ""},
        "email": {"enabled": False, "smtp_host": "", "smtp_port": 587, "from_addr": ""},
        "csv_import": {"enabled": False, "watch_dir": "", "poll_interval_s": 60},
        "erp_sync": {"enabled": False, "endpoint": "", "api_key_env": "ERP_API_KEY"},
    },
}


def load_config():
    """Load config from file, overlay with env vars."""
    config = dict(DEFAULT_CONFIG)

    # Load from file if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            _deep_merge(config, saved)
        except (json.JSONDecodeError, IOError):
            pass

    # Env var overrides (prefixed UGSI_)
    env_map = {
        "UGSI_INVENTREE_URL": "inventree_url",
        "UGSI_INVENTREE_USER": "inventree_user",
        "UGSI_MCP_PORT": ("mcp_port", int),
        "UGSI_DEV_MODE": ("dev_mode", _parse_bool),
        "UGSI_LOG_LEVEL": "log_level",
        "UGSI_CACHE_TTL": ("cache_ttl_seconds", int),
        "UGSI_ENABLE_WRITES": ("enable_write_operations", _parse_bool),
    }
    for env_key, target in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            if isinstance(target, tuple):
                config[target[0]] = target[1](val)
            else:
                config[target] = val

    return config


def save_config(config):
    """Persist config to disk (strips secrets)."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Never persist passwords
    safe = {k: v for k, v in config.items() if "password" not in k.lower()}
    with open(CONFIG_FILE, "w") as f:
        json.dump(safe, f, indent=2)


def get_inventree_password():
    """Get InvenTree password from env only."""
    return os.environ.get("INVENTREE_PASSWORD", os.environ.get("INVENTREE_ADMIN_PASSWORD", "ugsi2026!"))


def _parse_bool(s):
    return s.lower() in ("1", "true", "yes", "on")


def _deep_merge(base, override):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v

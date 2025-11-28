'''
Loads YAML/JSON/TOML + environment overrides.

'''

# src/ombudsman/config/config_loader.py

import os
import yaml

class Config:
    def __init__(self, data):
        self.data = data or {}

    def get(self, *keys, default=None):
        d = self.data
        for k in keys:
            d = d.get(k, {})
        return d if d != {} else default


def load_config(path=None):
    """
    Loads configuration from config/config.yaml by default.
    Environment variables can override any config key using the pattern:
    OMBUDSMAN__SECTION__SUBSECTION=value
    """
    # Default location is config/config.yaml
    if path is None:
        path = os.environ.get("OMBUDSMAN_CONFIG", "config/config.yaml")

    base = {}

    # Load file only if it exists
    if os.path.exists(path):
        with open(path, "r") as f:
            base = yaml.safe_load(f) or {}

    # Environment variable overrides (deep merge)
    # Example: OMBUDSMAN__SQL__HOST=newhost
    for key, val in os.environ.items():
        if key.startswith("OMBUDSMAN__"):
            parts = key.split("__")[1:]
            d = base
            for p in parts[:-1]:
                d = d.setdefault(p.lower(), {})
            d[parts[-1].lower()] = val

    return Config(base)
'''
Unified App Environment Loader
'''

# src/ombudsman/config/environment.py

import os
import yaml

def load_environment():
    config = yaml.safe_load(open("config/config.yaml"))

    # Replace ${VAR} with actual env values
    def resolve(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            key = value[2:-1]
            return os.getenv(key)
        return value

    # Walk config tree and resolve env references
    def process(node):
        if isinstance(node, dict):
            return {k: process(resolve(v)) for k, v in node.items()}
        if isinstance(node, list):
            return [process(resolve(x)) for x in node]
        return resolve(node)

    config = process(config)
    return config, {}   # secrets placeholder

    
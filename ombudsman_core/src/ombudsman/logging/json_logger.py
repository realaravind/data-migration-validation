# src/ombudsman/logging/json_logger.py

import json
import sys

class JsonLogger:
    def log(self, record):
        sys.stdout.write(json.dumps(record) + "\n")
        sys.stdout.flush()
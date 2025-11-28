# src/ombudsman/core/result.py
'''
Standard shape for all validator outputs.

'''

from datetime import datetime

class ValidationResult:
    def __init__(self, name, status, severity=None, details=None):
        self.name = name
        self.status = status
        self.severity = severity or "NONE"
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp
        }
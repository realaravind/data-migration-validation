'''
Abstracts secrets access.
'''

# src/ombudsman/config/secrets.py

import os

class SecretsProvider:
    def get(self, name):
        return os.environ.get(name)

        
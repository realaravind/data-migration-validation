# src/ombudsman/core/registry.py
'''
Central location where all validators are registered.

'''
class ValidationRegistry:
    def __init__(self):
        self.registry = {}

    def register(self, name, func, category):
        self.registry[name] = {
            "func": func,
            "category": category
        }

    def get(self, name):
        return self.registry.get(name)

    def list_all(self):
        return list(self.registry.keys())


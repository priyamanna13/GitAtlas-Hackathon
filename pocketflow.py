"""
PocketFlow stub — minimal implementation for local use.
The real pocketflow package (pip install pocketflow) provides these base classes.
This stub ensures the app runs even if pocketflow isn't installed via pip.
"""


class Node:
    """Base node class for PocketFlow pipeline."""

    def __init__(self, max_retries=1, wait=0):
        self.max_retries = max_retries
        self.wait = wait
        self._next = {}

    def prep(self, shared):
        return None

    def exec(self, prep_res):
        return None

    def post(self, shared, prep_res, exec_res):
        return "default"

    def run(self, shared):
        prep_res = self.prep(shared)
        exec_res = self.exec(prep_res)
        action = self.post(shared, prep_res, exec_res)
        return action

    def __rshift__(self, other):
        """Support node1 >> node2 syntax."""
        self._next["default"] = other
        return other

    def __sub__(self, action):
        """Support node - 'action' >> next_node syntax."""
        return _ConditionalConnector(self, action)


class _ConditionalConnector:
    def __init__(self, node, action):
        self.node = node
        self.action = action

    def __rshift__(self, other):
        self.node._next[self.action] = other
        return other


class Flow:
    """Sequential pipeline flow."""

    def __init__(self, start: Node):
        self.start = start

    def run(self, shared: dict):
        current = self.start
        while current is not None:
            action = current.run(shared)
            current = current._next.get(action) or current._next.get("default")
        return shared

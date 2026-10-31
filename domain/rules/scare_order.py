import random


class NoRepeatOrder:
    """Hands out items at random without repeating any until all have been used (or in order, if asked)."""

    def __init__(self, items, sequence=False, rng=None):
        self.items = list(items)
        self.sequence = sequence
        self.rng = rng or random.Random()
        self.queue = []

    def next(self):
        if not self.items:
            return None
        if not self.queue:
            self.queue = list(self.items) if self.sequence else self.rng.sample(self.items, len(self.items))
            if self.sequence:
                self.queue.reverse()
        return self.queue.pop()

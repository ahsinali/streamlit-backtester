class BarCursor:
    def __init__(self, n):
        self.n = n; self.i = 0
    def next(self):
        if self.i < self.n-1: self.i += 1
    def prev(self):
        if self.i > 0: self.i -= 1

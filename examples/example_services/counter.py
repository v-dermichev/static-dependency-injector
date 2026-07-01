from typing import ClassVar


class Counter:
    count: ClassVar = 0

    def __init__(self):
        Counter.count += 1

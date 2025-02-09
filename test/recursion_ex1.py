import test.recursion_ex2

from typing import Callable

func0 = lambda x: 0

func0b: Callable[[int], int] = lambda x: 0

def func1(x: int) -> int:
    return 0

def func2(x: int) -> int:
    inner: Callable[[int], int] = lambda x: 0 if x == 0 else inner(x - 1)
    return inner(x)

def func2b(x: int) -> int:
    inner: Callable[[int], int] = lambda x: 0 if x == 0 else inner(x - 1)
    return inner(x)

def func3(x: int) -> int:
    def inner(x: int) -> int:
        if x == 0:
            return 0
        return inner(x - 1)
    return test.recursion_ex2.hehe(inner(x))

def func4(x: int) -> int:
    if x == 0:
        return 0
    return func4(x - 1)

def func5(x: int) -> int:
    return func4(x)

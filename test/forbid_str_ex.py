import math
import string

def bad1() -> str:
    return str(24)

def bad2() -> str:
    return string.ascii_letters

def bad3() -> str:
    return f"{4}!"

def bad4() -> str:
    return f"{4}"

def bad5() -> str:
    return repr([])

def ok1() -> int:
    def foo(x: int) -> str:
        return str(x) + "!"
    return 23

def ok2() -> float:
    return math.sqrt(4.2)

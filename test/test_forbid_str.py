import sys
sys.path.append("../")

import ast_check
import common

import math
import string

uses_str_fmt = common.make_binary_nodep_check(ast_check.nodep_forbid_str_fmt)

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

def main() -> None:
    sources = common.read_sources([
        "test_forbid_str.py",
    ])
    [this] = list(sources.keys())

    for func_name, expect in [
            ("bad1", True),
            ("bad2", True),
            ("bad3", True),
            ("bad4", True),
            ("bad5", True),
            ("ok1", False),
            ("ok2", False),
       ]:
        func = eval(func_name)
        assert uses_str_fmt(sources, this, func, func_name) == expect, f"{func_name} should yield {expect}"

    print("OK")

if __name__ == "__main__":
    main()

import sys
sys.path.append("../")

from ast_analyze import *
from cases import *
import ast_check
import test_recursion_ext

from pathlib import PurePath
from typing import List, Callable, Optional, Any, Set, Dict
import cmath
import common
import math

def uses_float_op(sources: Dict[PurePath, str], func_def_path: PurePath, func: Callable[..., Any], func_name: str) -> Optional[bool]:
    funcs = collect_funcs(sources.items())
    graph_root = identify_func(funcs, func_def_path, func, func_name)

    # can't do anything if we can't find the function definition
    if graph_root is None:
        return None

    # call node predicate on the top level nodes of each called function
    summary = ast_check.Summary(1)
    ast_check.call_node_predicate(ast_check.nodep_forbid_float, summary, graph_root, set())

    return len(summary) != 0

def div() -> float:
    return 4 / 3

def const() -> float:
    return 6.9

def math_func() -> float:
    return math.sqrt(3)

def math_var() -> float:
    return math.pi

def bad1() -> float:
    return div()

def bad2() -> float:
    return const()

def bad3() -> float:
    return math_func()

def bad4() -> float:
    return math_var()

def ok1() -> int:
    return 3 // 2

def ok2() -> int:
    return ok1()

def ok3() -> int:
    func = lambda x: float(x)
    return ok1()

def ok4() -> int:
    class Vec2:
        x: float
        y: float

        def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
            self.x = x
            self.y = y

        def add(self, rhs: Vec2) -> None:
            self.x += rhs.x
            self.y += rhs.y

    return ok3()

def main() -> None:
    sources = common.read_sources([
        "test_forbid_float.py",
    ])
    [this] = list(sources.keys())

    for func_name in [
            "div",
            "const",
            "math_func",
            "math_var",
            "bad1",
            "bad2",
            "bad3",
            "bad4",
       ]:
        func = eval(func_name)
        assert uses_float_op(sources, this, func, func_name)

    for func_name in [
            "ok1",
            "ok2",
            "ok3",
            "ok4",
       ]:
        func = eval(func_name)
        assert not uses_float_op(sources, this, func, func_name)

    print("OK")

if __name__ == "__main__":
    main()

import sys
sys.path.append("../")

from ast_analyze import *
from cases import *
import ast_check
import test_recursion_ext

from typing import List, Callable, Optional, Any
import cmath
import math

def uses_float_op(source_paths: List[str], sources: List[str], func: Callable[..., Any], func_def_path: str) -> Optional[bool]:
    def call_node_predicate(node_predicate: NodePredicate, summary: ast_check.Summary,
                            func: Func, seen: Set[Func]) -> None:
        if func in seen:
            return
        seen.add(func)

        (node_predicate)(summary, func.body, func.source_path)

        for called in func.calls:
            call_node_predicate(node_predicate, summary, called, seen)

    (funcs, graph_root) = collect_funcs(source_paths, sources, func, func_def_path)

    # can't do anything if we can't find the function definition
    if graph_root is None:
        return None

    # call node predicate on the top level nodes of each called function
    summary = ast_check.Summary(1)
    call_node_predicate(ast_check.nodep_forbid_float, summary, graph_root, set())

    return len(summary) != 0

def div():
    return 4 / 3

def const():
    return 6.9

def math_func():
    return math.sqrt(3)

def math_var():
    return math.pi

def bad1():
    return div()

def bad2():
    return const()

def bad3():
    return math_func()

def bad4():
    return math_var()

def ok1():
    return 3 // 2

def ok2():
    return ok1()

def ok3():
    func = lambda x: float(x)
    return ok1()

def ok4():
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

sources = []
source_paths = ["test_forbid_float.py"]
for path in source_paths:
    with open(path, "r") as f:
        sources.append(f.read())
[this] = source_paths

for func in [
        div,
        const,
        math_func,
        math_var,
        bad1,
        bad2,
        bad3,
        bad4,
]:
    assert uses_float_op(source_paths, sources, func, this)

for func in [
        ok1,
        ok2,
        ok3,
        ok4,
]:
    assert not uses_float_op(source_paths, sources, func, this)

print("OK")

import sys
sys.path.append("../")

from ast_analyze import *
import ast_check
import test_recursion_ext

from typing import List, Callable, Optional, Any
import cmath
import math

def uses_float_op(source_names: List[str], sources: List[str], func: Callable[..., Any], func_def_path: str) -> Optional[bool]:
    (funcs, graph_root) = collect_funcs(source_names, sources, func, func_def_path)
    if graph_root is None:
        return None
    return not ast_check.forbid_float(graph_root, set())

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

sources = []
source_names = ["test_forbid_float.py"]
for path in source_names:
    with open(path, "r") as f:
        sources.append(f.read())
[this] = source_names

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
    assert uses_float_op(source_names, sources, func, this)

for func in [
        ok1,
        ok2,
]:
    assert not uses_float_op(source_names, sources, func, this)

print("OK")

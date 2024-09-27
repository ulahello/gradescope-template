import sys
sys.path.append("../")

from ast_analyze import *
import ast_check
import test_recursion_ext

from typing import List, Callable, Optional, Any

def check_rec_ast_cycles(source_names: List[str], sources: List[str], func_def_path: str, func: Callable[..., Any], func_name: str) -> Optional[bool]:
    (funcs, graph_root) = collect_funcs(source_names, sources, func_def_path, func, func_name)
    if graph_root is None:
        return None
    return ast_check.graphp_check_recursion(graph_root, set())

func0 = lambda x: 0

def func1(x: int) -> int:
    return 0

def func2(x: int) -> int:
    inner = lambda x: 0 if x == 0 else inner(x - 1) # type: ignore
    return inner(x) # type: ignore

def func2b(x: int) -> int:
    inner: Callable[[int], int] = lambda x: 0 if x == 0 else inner(x - 1)
    return inner(x)

def func3(x: int) -> int:
    def inner(x: int) -> int:
        if x == 0:
            return 0
        return inner(x - 1)
    return test_recursion_ext.hehe(inner(x))

def func4(x: int) -> int:
    if x == 0:
        return 0
    return func4(x - 1)

def func5(x: int) -> int:
    return func4(x)

sources = []
source_names = ["test_recursion.py", "test_recursion_ext.py"]
for path in source_names:
    with open(path, "r") as f:
        sources.append(f.read())


for func_name, expect in [
        ("func0", False),
        ("func1", False),
        ("func2", True),
        ("func2b", True), # FIXME: fails
        ("func3", True),
        ("func4", True),
        ("func5", True),
]:
    func = eval(func_name)
    assert check_rec_ast_cycles(source_names, sources, "test_recursion.py", func, func_name) == expect, f"{func_name} should yield {expect}"

print("OK")

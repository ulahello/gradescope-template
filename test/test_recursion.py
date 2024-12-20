import sys
sys.path.append("../")

from ast_analyze import *
import ast_check
import common
import test_recursion_ext

from pathlib import PurePath
from typing import List, Callable, Optional, Dict, Any

def check_rec_ast_cycles(sources: Dict[PurePath, str], func_def_path: PurePath, func: Callable[..., Any], func_name: str) -> Optional[bool]:
    funcs = collect_funcs(sources.items())
    graph_root = identify_func(funcs, func_def_path, func, func_name)
    if graph_root is None:
        return None
    return ast_check.graphp_check_recursion(graph_root, set())

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
    return test_recursion_ext.hehe(inner(x))

def func4(x: int) -> int:
    if x == 0:
        return 0
    return func4(x - 1)

def func5(x: int) -> int:
    return func4(x)

def main() -> None:
    sources = common.read_sources([
        "test_recursion.py",
        "test_recursion_ext.py",
    ])

    for func_name, expect in [
            ("func0", False),
            ("func0b", False),
            ("func1", False),
            ("func2", True),
            ("func2b", True),
            ("func3", True),
            ("func4", True),
            ("func5", True),
       ]:
        func = eval(func_name)
        assert check_rec_ast_cycles(sources, PurePath("test_recursion.py"), func, func_name) == expect, f"{func_name} should yield {expect}"

    print("OK")

if __name__ == "__main__":
    main()

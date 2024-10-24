import sys
sys.path.append("../")

from ast_analyze import *
from cases import *
import ast_check
import test_recursion_ext

from typing import List, Callable, Optional, Any, Set
import cmath
import math
import string

def uses_str_fmt(source_paths: List[str], sources: List[str], func_def_path: str, func: Callable[..., Any], func_name: str) -> Optional[bool]:
    funcs = collect_funcs(source_paths, sources)
    graph_root = identify_func(funcs, func_def_path, func, func_name)

    # can't do anything if we can't find the function definition
    if graph_root is None:
        return None

    # call node predicate on the top level nodes of each called function
    summary = ast_check.Summary(1)
    ast_check.call_node_predicate(ast_check.nodep_forbid_str_fmt, summary, graph_root, set())

    return len(summary) != 0

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
    sources = []
    source_paths = ["test_forbid_str.py"]
    for path in source_paths:
        with open(path, "r") as f:
            sources.append(f.read())
    [this] = source_paths

    for func_name, expect in [
            ("bad1", True),
            ("bad2", True),
            ("bad3", True),
            # ("bad4", True), # FIXME: fails
            ("bad5", True),
            ("ok1", False),
            ("ok2", False),
       ]:
        func = eval(func_name)
        assert uses_str_fmt(source_paths, sources, this, func, func_name) == expect, f"{func_name} should yield {expect}"

    print("OK")

if __name__ == "__main__":
    main()

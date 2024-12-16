from ast_analyze import *
from cases import *
import ast_check

from pathlib import PurePath
from typing import Dict, List, Optional, Callable, Any

def read_sources(paths: List[str]) -> Dict[PurePath, str]:
    sources = {}
    for path in paths:
        with open(path, "r") as f:
            sources[PurePath(path)] = f.read()
    return sources

def make_binary_nodep_check(nodep: ast_check.NodePredicate) -> Callable[
    [Dict[PurePath, str], PurePath, Callable[..., Any], str],
    Optional[bool]
]:
    def inner(sources: Dict[PurePath, str], func_def_path: PurePath, func: Callable[..., Any], func_name: str) -> Optional[bool]:
        funcs = collect_funcs(sources.items())
        graph_root = identify_func(funcs, func_def_path, func, func_name)

        # can't do anything if we can't find the function definition
        if graph_root is None:
            return None

        # call node predicate on the top level nodes of each called function
        summary = ast_check.Summary(1)
        ast_check.call_node_predicate(nodep, summary, graph_root, set())

        return len(summary) != 0

    return inner

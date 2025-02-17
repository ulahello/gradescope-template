from ast_analyze import *
from cases import *
import ast_check

from pathlib import PurePath
from types import ModuleType
from typing import Dict, List, Optional, Callable, Any, Iterable

def check_rec_ast_cycles(sources: Iterable[ModuleType], func_def_mod: ModuleType, func: Callable[..., Any], func_name: str) -> Optional[bool]:
    funcs = collect_funcs(sources)
    graph_root = identify_func(funcs, func_def_mod, func, func_name)
    if graph_root is None:
        return None
    return ast_check.graphp_check_recursion(graph_root, set())

def make_binary_nodep_check(nodep: ast_check.NodePredicate) -> Callable[
    [Iterable[ModuleType], ModuleType, Callable[..., Any], str],
    Optional[bool]
]:
    def inner(sources: Iterable[ModuleType], func_def_mod: ModuleType, func: Callable[..., Any], func_name: str) -> Optional[bool]:
        funcs = collect_funcs(sources)
        graph_root = identify_func(funcs, func_def_mod, func, func_name)

        # can't do anything if we can't find the function definition
        if graph_root is None:
            return None

        # call node predicate on the top level nodes of each called function
        summary = ast_check.Summary(1)
        ast_check.call_node_predicate(nodep, summary, graph_root, set())

        return len(summary) != 0

    return inner

uses_str_fmt = make_binary_nodep_check(ast_check.nodep_forbid_str_fmt)
uses_float_op = make_binary_nodep_check(ast_check.nodep_forbid_float)

from core import *
from ast_analyze import *

from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import ast

def check_cycle(root: Func, seen: Set[Func]) -> bool:
    for call in root.calls:
        if call in seen:
            # found a cycle
            return True
        seen.add(call)
        if check_cycle(call, seen):
            return True
    return False

def check_rec_ast_cycles(source_names: Iterable[str], sources: Iterable[str], func: Callable[..., Any], func_def_path: str) -> Optional[bool]:
    (funcs, graph_root) = collect_funcs(source_names, sources, func, func_def_path)
    if graph_root is None:
        # can't analyze this, the function wasn't found
        return None
    return check_cycle(graph_root, set())

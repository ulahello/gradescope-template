"""Use analyzed AST info from ast_analyze to make decisions about submissions.
See `cases.CaseCheckAst`.

Functions prefixed with "nodep_" or "graphp_" are usable as node and
graph predicates respectively for CaseCheckAst.
"""

from ast_analyze import *

from typing import Optional, Set, List, Tuple, Sequence, Any, Type
import ast

class Cause:
    fname: str
    node_cause: ast.AST
    msg: str

    def __init__(self, fname: str, node_cause: ast.AST, msg: str) -> None:
        self.fname = fname
        self.node_cause = node_cause
        assert len(msg.splitlines()) == 1, f"invalid {msg=}, must be one line"
        self.msg = msg.strip()

    def __repr__(self) -> str:
        return f"Error({repr(self.msg)}, node={self.node_cause})"

class Summary:
    max_to_report: int
    _whys: List[Cause]

    def __init__(self, max_to_report: int = 4) -> None:
        assert 0 < max_to_report, f"{max_to_report=} must be positive integer"
        self.max_to_report = max_to_report
        self._whys = []

    def __len__(self) -> int:
        return len(self._whys)

    def __repr__(self) -> str:
        return f"Summary(max={self.max_to_report}, {repr(self._whys)})"

    def unreported(self) -> int:
        return max(0, len(self) - self.max_to_report)

    def is_truncated(self) -> bool:
        return 0 < self.unreported()

    def report(self, why: Cause) -> None:
        self._whys.append(why)

    def whys(self) -> List[Cause]:
        return self._whys[:self.max_to_report]

# TODO: (node predicate approach): nested function definitions are considered executed code because we just ast.walk(top_node)

def forbid_funcalls(summary: Summary, top_node: ast.AST, fname: str,
                    forbidden_funcs: Sequence[Tuple[Optional[str], str]]) -> None:
    for node in ast.walk(top_node):
        if isinstance(node, ast.Call):
            for func in forbidden_funcs:
                (func_mod, func_name) = func
                if check_call_eq(func, node) == True:
                    msg: str = f"the function `{func_name}`"
                    if func_mod is not None:
                        msg += f" from the module `{func_mod}`"
                    msg += "is forbidden"
                    why = Cause(fname, node, msg)
                    summary.report(why)

def forbid_vars(summary: Summary, top_node: ast.AST, fname: str,
                forbidden_vars: Sequence[Tuple[str, str]]) -> None:
    for node in ast.walk(top_node):
        if isinstance(node, ast.Attribute) or isinstance(node, ast.Name):
            for spec in forbidden_vars:
                (mod_name, var_name) = spec
                if check_var_eq(spec, node) == True:
                    msg: str = f"the variable `{var_name}` from the module `{mod_name}` is forbidden"
                    why = Cause(fname, node, msg)
                    summary.report(why)

def forbid_modules(summary: Summary, top_node: ast.AST, fname: str,
                   forbidden_mods: Sequence[str]) -> None:
    for node in ast.walk(top_node):
        if isinstance(node, ast.Attribute) or isinstance(node, ast.Name):
            for mod_name in forbidden_mods:
                if check_mod_eq(mod_name, node) == True:
                    msg: str = f"the module `{mod_name}` is forbidden"
                    why = Cause(fname, node, msg)
                    summary.report(why)

def forbid_literals_of_type(summary: Summary, top_node: ast.AST, fname: str,
                            forbidden_types: Sequence[Type[Any]]) -> None:
    for node in ast.walk(top_node):
        if isinstance(node, ast.Constant):
            for ty in forbidden_types:
                if isinstance(node.value, ty):
                    msg: str = f"`{ty.__name__}` literals are forbidden"
                    why = Cause(fname, node, msg)
                    summary.report(why)

def forbid_ops(summary: Summary, top_node: ast.AST, fname: str,
               forbidden_ops: List[Tuple[Type[ast.AST], str]]) -> None:
    for node in ast.walk(top_node):
        if isinstance(node, ast.BinOp):
            for bad_op, symbol in forbidden_ops:
                if isinstance(node.op, bad_op):
                    msg: str = f"`{symbol}` operators are forbidden"
                    why = Cause(fname, node, msg)
                    summary.report(why)

def p_forbid_str_fmt(summary: Summary, top_node: ast.AST, fname: str) -> None:
    # TODO: inherently heuristic

    forbid_funcalls(summary, top_node, fname, [
        (None, "str"),
        (None, "repr"),
    ])

    forbid_literals_of_type(summary, top_node, fname, [
        str,
    ])

def p_forbid_float(summary: Summary, top_node: ast.AST, fname: str) -> None:
    # TODO: inherently heuristic

    forbid_funcalls(summary, top_node, fname, [
        (None, "complex"),
        (None, "float"),

        # functions in `math`
        ("math", "fabs"),
        ("math", "fmod"),
        ("math", "frexp"),
        ("math", "fsum"),
        ("math", "ldexp"),
        ("math", "modf"),
        ("math", "nextafter"),
        ("math", "remainder"),
        ("math", "ulp"),
        ("math", "cbrt"),
        ("math", "exp"),
        ("math", "exp2"),
        ("math", "expm1"),
        ("math", "log"),
        ("math", "log1p"),
        ("math", "log2"),
        ("math", "log10"),
        ("math", "pow"),
        ("math", "sqrt"),
        ("math", "acos"),
        ("math", "asin"),
        ("math", "atan"),
        ("math", "atan2"),
        ("math", "cos"),
        ("math", "dist"),
        ("math", "hypot"),
        ("math", "sin"),
        ("math", "tan"),
        ("math", "degrees"),
        ("math", "radians"),
        ("math", "acosh"),
        ("math", "asinh"),
        ("math", "atanh"),
        ("math", "cosh"),
        ("math", "sinh"),
        ("math", "tanh"),
        ("math", "erf"),
        ("math", "erfc"),
        ("math", "gamma"),
        ("math", "lgamma"),
    ])

    forbid_vars(summary, top_node, fname, [
        ("math", "pi"),
        ("math", "e"),
        ("math", "tau"),
        ("math", "inf"),
        ("math", "nan"),
    ])

    forbid_modules(summary, top_node, fname, [
        "cmath",
    ])

    forbid_literals_of_type(summary, top_node, fname, [
        float,
        complex,
    ])

    forbid_ops(summary, top_node, fname, [
        (ast.Div, "/"),
    ])

def check_call_graph_cycle(root: Func, seen: Set[Func]) -> bool:
    if root in seen:
        return True
    seen.add(root)

    for call in root.calls:
        if check_call_graph_cycle(call, seen):
            return True
    return False

"""Use analyzed AST info from ast_analyze to make decisions about submissions.
See `cases.CaseCheckAst`."""

from ast_analyze import *

from typing import Optional, Set, List, Tuple
import ast

def forbid_str_fmt(root: Func, seen: Set[Func]) -> Optional[bool]:
    if root in seen:
        return True
    seen.add(root)

    FORBIDDEN_FUNCS: List[Tuple[Optional[str], str]] = [
        (None, "str"),
        (None, "repr"),
    ]

    # check this function
    for node in ast.walk(root.top_node):
        if isinstance(node, ast.Constant):
            for bad in [str]:
                if isinstance(node.value, bad):
                    return False

        if isinstance(node, ast.Call):
            if check_call_eq(FORBIDDEN_FUNCS, node) == True:
                return False

    # recursively check called functions
    for called in root.calls:
        ok = forbid_str_fmt(called, seen)
        if ok != True:
            return ok

    return True

def forbid_float(root: Func, seen: Set[Func]) -> Optional[bool]:
    # TODO: inherently heuristic

    FORBIDDEN_MODS: List[str] = [
        "cmath",
    ]

    FORBIDDEN_VARS: List[Tuple[str, str]] = [
        ("math", "pi"),
        ("math", "e"),
        ("math", "tau"),
        ("math", "inf"),
        ("math", "nan"),
    ]

    FORBIDDEN_FUNCS: List[Tuple[Optional[str], str]] = [
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
    ]

    # if we've already seen this (in a cyclical call graph),
    # return True to be ignored (not semantically true)
    if root in seen:
        return True
    seen.add(root)

    # check this function
    for node in ast.walk(root.top_node):
        # binary division operators yield floats
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Div):
                return False

        # float literals yield floats
        if isinstance(node, ast.Constant):
            for bad in [float, complex]:
                if isinstance(node.value, bad):
                    return False

        # many functions in `math` yield floats
        if isinstance(node, ast.Call):
            if check_call_eq(FORBIDDEN_FUNCS, node) == True:
                return False
        if isinstance(node, ast.Name) or isinstance(node, ast.Attribute):
            if check_var_eq(FORBIDDEN_VARS, node) == True:
                return False
            if check_mod_eq(FORBIDDEN_MODS, node) == True:
                return False

    # recursively check called functions
    for called in root.calls:
        ok = forbid_float(called, seen)
        if ok != True:
            return ok

    return True

def check_call_graph_cycle(root: Func, seen: Set[Func]) -> bool:
    if root in seen:
        return True
    seen.add(root)

    for call in root.calls:
        if check_call_graph_cycle(call, seen):
            return True
    return False


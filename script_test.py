"""
This is "the autograder tests itself".
So long as the higher level testing code isn't tested by itself, I don't think the circular implications are particularly devastating.
"""

# TODO: external testing for higher level code that is not circular

from cases import *
from core import *
from _generics import *
from io_trace import Read, Write
from pipeline import *
from util import *
import ast_check
import cases
import cli
import io_trace
import util

import test.common
import test.forbid_float_ex
import test.forbid_str_ex
import test.recursion_ex1
import test.recursion_ex2

from pathlib import PurePath
from types import ModuleType
from typing import Dict, List, Any, Optional, Callable, Tuple
import random

def get_test_cases(metadata: JsonMetadata) -> List[Case]:
    def mk_case(visible: bool, func: Callable[..., T], args: Tuple[Any, ...], ret_expect: T) -> CaseFunc[T]:
        return CaseFunc(visible, func, f"{func.__name__}{fmt_args(args)}",
                        args=args,
                        ret_expect=ret_expect)

    cases: List[Case] = []
    expect: Any

    # 'util' module
    for args, expect in [
            (([2, 2, 3], [2, 3, 2]), True),
            (([2, 2, 3], [2, 3, 2]), True),
            (([2, 2, 3], [2, 0, 2]), False),
            (([2, 2, 3], [2, 2]), False),
            (([2, 2, 3], [2, 3]), False),
            (([["foo"], ["bar"], ["bar"]], [["bar"], ["bar"], ["foo"]]), True),
            (([["foo"], ["bar"], ["bar"]], [["bar"], ["foo"]]), False),
    ]:
        cases.append(mk_case(True, util.cmp_ret_seq_freq, args, expect))

    # 'check_def_style'
    for func, expect in [
            (test.recursion_ex1.func0, (True, False)),
            (test.recursion_ex1.func0, (True, False)),
            (test.recursion_ex1.func0b, (True, False)),
            (test.recursion_ex1.func1, (False, True)),
            (test.recursion_ex1.func2, (False, True)),
            (test.recursion_ex1.func2b, (False, True)),
            (test.recursion_ex1.func3, (False, True)),
            (test.recursion_ex1.func4, (False, True)),
            (test.recursion_ex1.func5, (False, True)),
    ]:
        cases.append(mk_case(True, check_def_style, (func,), expect))

    # these TODOs are for the ast checks:
    # TODO: module path of the function should be here too, but without possible copy-paste errors
    # TODO: fragile paths
    # TODO: this sucks

    func_def_mod: ModuleType

    # recursion
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
        func_def_mod = test.recursion_ex1
        sources = [func_def_mod, test.recursion_ex2]
        func = getattr(func_def_mod, func_name)
        cases.append(
            CaseFunc(
                True, test.common.check_rec_ast_cycles, f"{func_name} is {'' if expect else 'not '}recursive",
                args=(sources, func_def_mod, func, func_name),
                ret_expect=expect,
            )
        )

    # string formatting detection
    for func_name, expect in [
            ("bad1", True),
            ("bad2", True),
            ("bad3", True),
            ("bad4", True),
            ("bad5", True),
            ("ok1", False),
            ("ok2", False),
    ]:
        func_def_mod = test.forbid_str_ex
        sources = [func_def_mod]
        func = getattr(func_def_mod, func_name)
        cases.append(
            CaseFunc(
                True, test.common.uses_str_fmt, f"{func_name} uses string formatting" if expect else f"{func_name} does not use string formatting",
                args=(sources, func_def_mod, func, func_name),
                ret_expect=expect,
            )
        )

    # float detection
    for func_name, expect in [
            ("div", True),
            ("const", True),
            ("math_func", True),
            ("math_var", True),
            ("bad1", True),
            ("bad2", True),
            ("bad3", True),
            ("bad4", True),
            ("ok1", False),
            ("ok2", False),
            ("ok3", False),
            ("ok4", False),
    ]:
        func_def_mod = test.forbid_float_ex
        sources = [func_def_mod]
        func = getattr(func_def_mod, func_name)
        cases.append(
            CaseFunc(
                True, test.common.uses_float_op, f"{func_name} uses floating point" if expect else f"{func_name} does not use floating point",
                args=(sources, func_def_mod, func, func_name),
                ret_expect=expect,
            )
        )

    return cases

if __name__ == "__main__":
    cli.main(get_test_cases)

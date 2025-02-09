"""
This is "the autograder tests itself".
So long as the higher level testing code isn't tested by itself, I don't think the circular implications are particularly devastating.
"""

from cases import *
from core import *
from _generics import *
from io_trace import Read, Write
from pipeline import *
from util import *
import ast_check
import cli
import io_trace
import util

from typing import Dict, List, Any, Optional, Callable, Tuple
import random

def get_test_cases(metadata: JsonMetadata) -> List[Case]:
    def mk_case(visible: bool, func: Callable[..., T], args: Tuple[Any, ...], ret_expect: T) -> CaseFunc[T]:
        return CaseFunc(visible, func, f"{func.__name__}{fmt_args(args)}",
                        args=args,
                        ret_expect=ret_expect)

    cases: List[Case] = [
        # test util
        mk_case(True, util.cmp_ret_seq_freq, ([2, 2, 3], [2, 3, 2]), True),
        mk_case(True, util.cmp_ret_seq_freq, ([2, 2, 3], [2, 3, 2]), True),
        mk_case(True, util.cmp_ret_seq_freq, ([2, 2, 3], [2, 0, 2]), False),
        mk_case(True, util.cmp_ret_seq_freq, ([2, 2, 3], [2, 2]), False),
        mk_case(True, util.cmp_ret_seq_freq, ([2, 2, 3], [2, 3]), False),
        mk_case(True, util.cmp_ret_seq_freq, ([["foo"], ["bar"], ["bar"]], [["bar"], ["bar"], ["foo"]]), True),
        mk_case(True, util.cmp_ret_seq_freq, ([["foo"], ["bar"], ["bar"]], [["bar"], ["foo"]]), False),
    ]

    return cases

if __name__ == "__main__":
    cli.main(get_test_cases)

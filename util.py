from core import AutograderError, Case, WHERE_THE_SUBMISSION_IS
from io_trace import Read, Write, LineIter

from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, Hashable, cast
import importlib
import importlib.util as iu
import inspect
import itertools
import json
import os

# TODO: would be nice to be able to check all expected attributes in one sweep and present all errors to student, rather than one-by-one (good compilers will do this, it is nice)

def cmp_attributes(obj: Any, required: Set[str]) -> Tuple[Set[str], Set[str]]: # -> (extra, missing)
    attrs: Set[str]
    try:
        attrs = set(obj.__dict__.keys())
    except AttributeError:
        attrs = set()
    extra = attrs.difference(required)
    missing = required.difference(attrs)
    return extra, missing

def get_attribute(obj: Any, attr: str, msg: str) -> Any:
    try:
        thing = getattr(obj, attr)
    except AttributeError as e:
        # choosing not to include the AttributeError because it
        # basically says the same information, but needlessly produces
        # a full stack trace.
        raise AutograderError(None, msg)
    return thing

def get_func(mod: Any, name: str) -> Callable[..., Any]:
    func = get_attribute(mod, name, f"Could not find function '{name}' in '{mod.__name__}'. Is it defined?")
    if callable(func):
        return func # type: ignore
    else:
        raise AutograderError(None, f"Found '{name}' in '{mod.__name__}', but it is not callable. Is it a function?")

def get_class(mod: Any, name: str) -> type:
    class_t = get_attribute(mod, name, f"Could not find class '{name}' in '{mod.__name__}'. Is it defined?")
    if inspect.isclass(class_t):
        return class_t
    else:
        raise AutograderError(None, f"Found '{name}' in '{mod.__name__}', but it is not a class.")

def check_subclass(this: Any, subclass_of: Any) -> None:
    if not issubclass(this, subclass_of):
        raise AutograderError(None, f"'{this.__name__}' must be a subclass of '{subclass_of.__name__}'.")

def expect_n_submissions(n: int) -> List[str]:
    files = []

    for entry in os.scandir(WHERE_THE_SUBMISSION_IS):
        if entry.is_file():
            files.append(entry.name)

    if len(files) != n:
        raise AutograderError(None, f"Expected exactly {n} file{'' if n == 1 else 's'} submitted, but found {len(files)}.")
    return files

submission_number: int = 0

def load_script(fname: str) -> Tuple[ModuleType, ModuleSpec]:
    try:
        return run_script(fname)
    except Exception as e:
        raise AutograderError(e, "Failed to load student submission.")

def run_script(fname: str) -> Tuple[ModuleType, ModuleSpec]:
    global submission_number
    submission_number += 1
    # TODO: don't make up module name, show the filename
    modname = f"student_submission_{submission_number}" # just want a unique module name that isn't insane

    location = f"{WHERE_THE_SUBMISSION_IS}/{fname}"
    spec: Optional[ModuleSpec] = iu.spec_from_file_location(modname, location)
    if spec is None:
        raise AutograderError(None, f"Python failed to load the submission '{fname}' and did not say why. Try checking the file extension?")

    loader: Optional[Loader] = spec.loader
    assert loader is not None, "docs say 'Finders should always set this'"

    mod: ModuleType = iu.module_from_spec(spec)
    loader.exec_module(mod) # @raise
    return mod, spec

def count_freq(iter: Iterable[Hashable]) -> Dict[Hashable, int]:
    f: Dict[Hashable, int] = {}
    for k in iter:
        f.setdefault(k, 0)
        f[k] += 1
    return f

def nth(rank: int) -> str:
    assert 0 <= rank
    suffix: str
    ones: int = rank % 10
    tens: int = (rank // 10) % 10
    if tens == 1:
        suffix = "th"
    elif ones == 1:
        suffix = "st"
    elif ones == 2:
        suffix = "nd"
    elif ones == 3:
        suffix = "rd"
    else:
        suffix = "th"
    return f"{rank}{suffix}"

def cmp_ret_nop(expect: Any, actual: Any) -> bool:
    return True

def cmp_ret_epsilon(expect: Any, actual: Any,
                    epsilon: float = 0.00001) -> bool: # @CHANGEME (or write your own)
    if not isinstance(actual, (int, float)):
        return False
    eq: bool = abs(expect - actual) < epsilon
    return eq

def cmp_ret_equ(expect: Any, actual: Any) -> bool:
    eq: bool = expect == actual
    return eq

def is_sequence(obj: Any) -> bool:
    for req in [
            "__getitem__",
            "__len__",
    ]:
        if not hasattr(obj, req):
            # it's not a sequence! i am weeping!
            return False
    return True

def cmp_ret_seq(cmp_elem: Callable[[Any, Any], bool]) -> Callable[[Sequence[Any], Sequence[Any]], bool]:
    def inner(expect: Sequence[Any], actual: Sequence[Any]) -> bool:
        if not is_sequence(actual):
            return False
        if len(expect) != len(actual):
            return False
        for expect_elem, actual_elem in zip(expect, actual):
            if not cmp_elem(expect_elem, actual_elem):
                return False
        return True

    return inner

# works with unhashable types!
def cmp_ret_seq_unordered(expect: Sequence[Any], actual: Any) -> bool:
    if not is_sequence(actual):
        return False
    if len(expect) != len(actual):
        return False
    for expect_item in expect:
        if not expect_item in actual:
            return False
    return True

# works with unhashable types!
def cmp_ret_seq_freq(expect: Sequence[Any], actual: Any) -> bool:
    if not is_sequence(actual):
        return False
    if len(expect) != len(actual):
        return False
    # XXX: love this time complexity for us
    for expect_item in expect:
        expect_count = expect.count(expect_item)
        if not actual.count(expect_item) == expect_count:
            return False
    return True

def cmp_io_equ(expect: List[Read | Write], actual: List[Read | Write]) -> bool:
    op_eq = lambda e, a: type(e) == type(a) and e.val == a.val
    return cmp_ret_seq(op_eq)(expect, actual)

def fmt_ret_s(expect: str, actual: str, eq: bool, prefix: str) -> str:
    output: str = f"{prefix}: "
    if eq:
        output += f"got `{actual}` as expected.\n"
    else:
        output += f"expected `{expect}`, but got `{actual}`.\n"
    return output

def fmt_ret(expect: Any, actual: Any, eq: bool, prefix: str) -> str:
    return fmt_ret_s(repr(expect), repr(actual), eq, prefix)

def fmt_io_equ(expect: List[Read | Write],
               actual: List[Read | Write],
               passed: bool) -> str:
    output: str = ""

    if passed and len(expect) != 0:
        output += "All console I/O lines match.\n"

    line: int = 0
    for le, la in itertools.zip_longest(LineIter(expect), LineIter(actual)):
        line += 1

        if le is None:
            output += f"Console line {line}: too many lines\n"
            return output
        elif la is None:
            output += f"Console line {line}: want additional line(s)\n"
            return output

        for oe, oa in itertools.zip_longest(le, la):
            if oe is None:
                output += f"Console line {line}: expected end of line, but found {oa.word()} of `{repr(oa.val)}`.\n"
                return output
            elif oa is None:
                output += f"Console line {line}: expected {oe.word()} of `{repr(oe.val)}`, but found end of line.\n"
                return output

            if type(oe) != type(oa):
                # mismatched read/write
                output += f"Console line {line}: expected {oe.word()} of `{repr(oe.val)}`, but found {oa.word()} of `{repr(oa.val)}`.\n"
                return output

            if oe.val != oa.val:
                output += f"Console line {line} ({oe.word()}): expected `{repr(oe.val)}`, but found `{repr(oa.val)}`.\n"
                return output

    return output

def fmt_io_verbatim(io: List[Read | Write]) -> str:
    output: str = ""
    for op in io:
        output += op.val
    return output

def fmt_args(args: Tuple[Any, ...]) -> str:
    if len(args) == 1:
        (arg,) = args
        return f"({repr(arg)})"
    return repr(args)

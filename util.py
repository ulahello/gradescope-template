from core import AutograderError, Case

from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import importlib
import importlib.util as iu
import inspect
import json
import os

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

    for entry in os.scandir("submission"):
        if entry.is_file():
            files.append(entry.name)

    if len(files) != n:
        raise AutograderError(None, f"Expected exactly {n} file{'' if n == 1 else 's'} submitted, but found {len(files)}.")
    return files

submission_number: int = 0
def run_script(fname: str) -> Tuple[ModuleType, ModuleSpec]:
    global submission_number
    submission_number += 1
    modname = f"student_submission_{submission_number}" # just want a unique module name that isn't insane

    spec: Optional[ModuleSpec] = iu.spec_from_file_location(modname, f"submission/{fname}")
    assert spec is not None, f"'{fname}' should exist"

    loader: Optional[Loader] = spec.loader
    assert loader is not None, "docs say 'Finders should always set this'"

    mod: ModuleType = iu.module_from_spec(spec)
    try:
        loader.exec_module(mod) # @raise
    except Exception as e:
        raise AutograderError(e, "Failed to load student submission.")
    return mod, spec

def cmp_ret_epsilon(expect: Any, actual: Any,
                    epsilon: float = 0.00001) -> bool: # @CHANGEME (or write your own)
    if not (isinstance(actual, int) or isinstance(actual, float)):
        return False
    eq: bool = abs(expect - actual) < epsilon
    return eq

def cmp_ret_equ(expect: Any, actual: Any) -> bool:
    eq: bool = expect == actual
    return eq

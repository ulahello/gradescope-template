from core import AutograderError, WHERE_THE_SUBMISSION_IS
from _generics import *

from importlib.abc import Loader, FileLoader
from importlib.machinery import ModuleSpec
from pathlib import PurePath
from types import ModuleType
from typing import List, Optional, Any, Callable, TypeAlias, Type, Tuple, cast
import importlib.util as iu
import inspect
import os

# TODO: expected attributes are sometimes specific to test cases, so presenting this in SummaryBad is more restrictive than strictly necessary

ModuleLike: TypeAlias = ModuleType | Type[Any]

# used instead of None to indicate that "the thing could not be
# loaded, but we continue because that's what a summary is" for easier
# time with type checking script_*.py
class _stub:
    pass

class LoadSummary:
    errors: List[AutograderError]
    returns: List[Type[_stub] | Any]
    summarized: bool

    def __init__(self) -> None:
        self.errors = []
        self.returns = []
        self.summarized = False

    def _shape(self, f: Callable[..., T], args: Tuple[Any, ...]) -> T:
        assert not self.summarized, "called LoadSummary.[get | check] after calling summarize()"
        if args[0] is _stub:
            assert 0 < len(self.errors)
        else:
            try:
                ret = f(*args)
                self.returns.append(ret)
                return ret
            except AutograderError as e:
                self.errors.append(e)
        return cast(T, _stub)

    def get_attribute(self, obj: Any, attr: str, msg: str) -> Any:
        return self._shape(_get_attribute, (obj, attr, msg))

    def get_func(self, mod: ModuleLike, name: str) -> Callable[..., Any]:
        return self._shape(_get_func, (mod, name))

    def get_class(self, mod: ModuleLike, name: str) -> Type[Any]:
        return self._shape(_get_class, (mod, name))

    def check_subclass(self, this: Type[Any], subclass_of: Type[Any]) -> Optional[Type[_stub]]:
        return self._shape(_check_subclass, (this, subclass_of))

    def summarize(self) -> None:
        self.summarized = True
        msg: str = f"# Issues\n"
        for error in self.errors:
            msg += f"- {error.msg}\n"
            assert error.inner is None
        if len(self.errors):
            raise AutograderError(None, msg)
        else:
            # there should be no errors! assert all definitions are loaded.
            for idx, ret in enumerate(self.returns):
                assert ret is not _stub, f"unreachable: missing definition {idx=} but no errors indicated"

def _get_attribute(obj: Any, attr: str, msg: str) -> Any:
    try:
        thing = getattr(obj, attr)
    except AttributeError as e:
        # choosing not to include the AttributeError because it
        # basically says the same information, but needlessly produces
        # a full stack trace.
        raise AutograderError(None, msg)
    return thing

def _display_mod_name(mod: ModuleLike, fallback: Optional[str]) -> str:
    if hasattr(mod, "__loader__"):
        loader = mod.__loader__
        if isinstance(loader, FileLoader):
            path = PurePath(loader.path)
            return f"file '{path.name}'"

    if inspect.isclass(mod):
        return f"class '{mod.__name__}'"

    if fallback is None:
        fallback = mod.__name__
    return f"'{fallback}'"

def _get_func(mod: ModuleLike, name: str, mod_name: Optional[str] = None) -> Callable[..., Any]:
    mod_name = _display_mod_name(mod, mod_name)
    func: Any | Callable[..., Any] = _get_attribute(mod, name, f"Could not find function '{name}' in {mod_name}.")
    if callable(func):
        return func
    else:
        raise AutograderError(None, f"Expected '{name}' in {mod_name} to be a function, but it has the type '{type(func).__name__}'.")

def _get_class(mod: ModuleLike, name: str, mod_name: Optional[str] = None) -> Type[Any]:
    mod_name = _display_mod_name(mod, mod_name)
    class_t = _get_attribute(mod, name, f"Could not find class '{name}' in {mod_name}.")
    if inspect.isclass(class_t):
        return class_t
    else:
        raise AutograderError(None, f"Expected '{name}' in {mod_name} to be a class, but it has the type '{type(class_t).__name__}'.")

def _check_subclass(this: Type[Any], subclass_of: Type[Any]) -> None:
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

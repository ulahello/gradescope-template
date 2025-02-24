from ast_analyze import *
from core import Case, AutograderError, WHERE_THE_SUBMISSION_IS
from io_trace import Read, Write
from util import *
import ast_check
import io_trace
import load
import util

from pathlib import PurePath
from types import ModuleType
from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Iterable, Sequence, TypeAlias, NamedTuple, Generic
import ast
import inspect

class CaseIOBase(Case):
    # List of read operations to pass to stdin. Popped from index 0.
    # When the queue is empty, defers to OS as expected.
    io_queue: List[str]

    # Expected sequence of console I/O operations to observe during a test.
    io_expect: List[Read | Write]

    # Observed sequence of console I/O operations during a test.
    io_actual: Optional[List[Read | Write]]

    # `True` if the expected I/O operations were observed.
    io_passed: Optional[bool]

    cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool]
    fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str]

    def __init__(self,
                 visible: bool,
                 name: str,
                 warning: bool,
                 io_queue: List[str],
                 io_expect: List[Read | Write],
                 cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool],
                 fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str]) -> None:
        super().__init__(visible, name=name, warning=warning)

        self.io_queue = io_queue
        # in case we're passed consecutive operations of the same
        # type, this will merge them (it's a pitfall otherwise)
        self.io_expect = io_trace.normalize_log(io_expect)
        self.io_actual = None
        self.io_passed = None
        self.cmp_io = cmp_io
        self.fmt_io = fmt_io

    def check_io_passed(self) -> bool:
        assert self.has_run
        assert self.io_expect is not None, "unreachable"
        assert self.io_actual is not None, "unreachable"

        return (self.cmp_io)(self.io_expect, self.io_actual)

    def check_passed(self) -> None:
        assert self.has_run
        assert self.io_expect is not None, "unreachable"
        assert self.io_actual is not None, "unreachable"

        self.io_passed = self.check_io_passed()
        self.passed = self.io_passed

    def run_post(self) -> None:
        assert not self.has_run, "case should only be run once"
        self.has_run = True
        self.check_passed()

    def run(self) -> None:
        assert False, "CaseIOBase.run should be overridden to suit use case"

    def format_console_io_check(self) -> str:
        assert self.has_run
        assert self.io_expect is not None, "unreachable"
        assert self.io_actual is not None, "unreachable"
        assert self.io_passed is not None, "unreachable"

        return (self.fmt_io)(self.io_expect, self.io_actual, self.io_passed)

    def format_output(self) -> str:
        return self.format_console_io_check()

class CaseAdHoc(Case):
    runner: Callable[["CaseAdHoc"], None]
    output: str

    def __init__(self,
                 visible: bool,
                 name: str,
                 runner: Callable[["CaseAdHoc"], None],
                 warning: bool = False) -> None:
        super().__init__(visible, name=name, warning=warning)

        self.runner = runner
        self.output = ""
        self.passed = True

    def run(self) -> None:
        (self.runner)(self)
        self.run_post()

    def run_func(
            self,
            func: Callable[[], T],
            io_queue: List[str] = [],
            msg: str = "An exception was raised while running a student function.",
    ) -> Tuple[T, bool, List[Read | Write]]:
        try:
            ret, eof, io_log = io_trace.capture(func, io_queue=io_queue)
        except Exception as e:
            raise AutograderError(e, msg)

        return ret, eof, io_log

    def run_script(self, script: str, io_queue: List[str] = []) -> List[Read | Write]:
        _, _, io_log = self.run_func(
            lambda: load.run_script(script),
            io_queue=io_queue,
            msg="An exception was raised while running a student script.",
        )
        return io_log

    def check_passed(self) -> None:
        pass

    def expect(self, expect: bool) -> bool:
        self.passed = self.passed and expect
        return expect

    def expect_eq(self, expect: Any, actual: Any,
                  msg_prefix: str,
                  cmp: Callable[[Any, Any], bool] = cmp_ret_equ,
                  silence_pass: bool = False) -> bool:
        assert len(msg_prefix.splitlines()) == 1

        eq: bool = cmp(expect, actual)
        if eq and silence_pass:
            pass
        else:
            self.print(fmt_ret(expect, actual, eq, msg_prefix), end="")

        self.passed = self.passed and eq
        return eq

    def expect_io(self,
                  expect: List[Read | Write],
                  actual: List[Read | Write],
                  silence_pass: bool = False,
                  cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
                  fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_diff) -> bool:
        expect = io_trace.normalize_log(expect)
        actual = io_trace.normalize_log(actual)

        io_passed: bool = cmp_io(expect, actual)
        output: str = fmt_io(expect, actual, io_passed)
        if io_passed and silence_pass:
            pass
        else:
            self.print(output, end="")

        self.passed = self.passed and io_passed
        return io_passed

    def print(self, line: str = "", end: str = "\n", new_line: bool = False) -> None:
        content: str = line + end
        if new_line and not self.output.endswith("\n"):
            self.output += "\n"
        self.output += content

    def format_output(self) -> str:
        return self.output

class CaseFunc(CaseIOBase, Generic[T]):
    func: Callable[..., T]
    args: Tuple[Any, ...]
    cmp_ret: Callable[[Any, Any], bool]
    ret_expect: Optional[T]
    ret_actual: Optional[T]
    ret_passed: Optional[bool]
    eof: Optional[bool] # if true, the return value should not be checked, and we assume the case fails

    def __init__(self,
                 visible: bool,
                 func: Callable[..., T],
                 name: str,
                 warning: bool = False,
                 args: Tuple[Any, ...] = (),
                 ret_expect: Optional[T] = None,
                 cmp_ret: Callable[[Any, Any], bool] = cmp_ret_equ,
                 io_queue: List[str] = [],
                 io_expect: List[Read | Write] = [],
                 cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
                 fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_diff) -> None:
        super().__init__(visible, name=name, warning=warning,
                         io_queue=io_queue, io_expect=io_expect,
                         cmp_io=cmp_io, fmt_io=fmt_io)
        self.func = func
        self.args = args
        self.cmp_ret = cmp_ret
        self.ret_expect = ret_expect
        self.ret_actual = None
        self.ret_passed = None
        self.eof = None

    def run(self) -> None:
        try:
            self.ret_actual, self.eof, self.io_actual = io_trace.capture(lambda: self.func(*self.args), self.io_queue)
        except Exception as e:
            raise AutograderError(e, "An exception was raised while running a student function.")

        self.run_post()

    def check_ret_passed(self) -> bool:
        if self.eof == True:
            return False
        return (self.cmp_ret)(self.ret_expect, self.ret_actual)

    def check_passed(self) -> None:
        assert self.has_run
        self.io_passed = self.check_io_passed()
        self.ret_passed = self.check_ret_passed()
        self.passed = self.io_passed and self.ret_passed

    def format_output(self) -> str:
        assert self.has_run
        assert self.ret_passed is not None, "unreachable"
        assert self.eof is not None, "unreachable"

        output: str = ""
        if not self.eof:
            output += fmt_ret(self.ret_expect, self.ret_actual, self.ret_passed, "Return value")
        output += self.format_console_io_check()
        return output

class CaseScript(CaseIOBase):
    def __init__(self,
                 visible: bool,
                 script: str,
                 name: str,
                 warning: bool = False,
                 io_queue: List[str] = [],
                 io_expect: List[Read | Write] = [],
                 cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
                 fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ) -> None:
        super().__init__(visible, name=name, warning=warning,
                         io_queue=io_queue, io_expect=io_expect,
                         cmp_io=cmp_io, fmt_io=fmt_io)
        self.script = script

    def run(self) -> None:
        try:
            _, _, self.io_actual = io_trace.capture(lambda: load.run_script(self.script), self.io_queue)
        except Exception as e:
            raise AutograderError(e, "An exception was raised while running a student script.")

        self.run_post()

CHECK_AST_MAX_DIAGNOSTICS_DEFAULT: int = 4

# bundle of data used to instantiate source node predicates
class SourceSpec(NamedTuple):
    sources: List[ModuleType]

# bundle of data used to instantiate func node predicates
class FuncSpec(NamedTuple):
    func: Callable[..., Any]
    func_name: Optional[str] # if none, based on func.__code__.co_name
    func_def_mod: ModuleType
    sources: List[ModuleType]

    def resolve_func_name(self) -> str:
        if self.func_name is not None:
            return self.func_name
        else:
            return self.func.__code__.co_name

    def identify_func(self, funcs: List[Func]) -> Optional[Func]:
        return identify_func(
            funcs,
            self.func_def_mod,
            self.func,
            self.func_name,
        )

# optional component to CaseCheckAst that performs a basic check on a function in the call graph
class GraphP:
    predicate: ast_check.GraphPredicate
    spec: FuncSpec

    # filled in during use
    graph_root: Optional[Func]

    def __init__(self, predicate: ast_check.GraphPredicate,
                 spec: FuncSpec) -> None:
        self.predicate = predicate
        self.spec = spec

        self.graph_root = None

# optional component to CaseCheckAst that performs a complex check on a function in the call graph
class FuncNodeP:
    predicate: ast_check.NodePredicate
    spec: FuncSpec

    # filled in during use
    graph_root: Optional[Func]

    def __init__(self, predicate: ast_check.NodePredicate,
                 spec: FuncSpec) -> None:
        self.predicate = predicate
        self.spec = spec

        self.graph_root = None

# optional component to CaseCheckAst that performs a complex check on a source file's AST
class SourceNodeP:
    predicate: ast_check.NodePredicate
    sources: List[ModuleType]

    def __init__(self, predicate: ast_check.NodePredicate,
                 sources: List[ModuleType]) -> None:
        self.predicate = predicate
        self.sources = sources

class CaseCheckAst(Case):
    sources: Set[ModuleType]

    # components that are each checked
    graph_p: Optional[GraphP]
    func_node_p: Optional[FuncNodeP]
    source_node_p: Optional[SourceNodeP]

    summary: ast_check.Summary

    pass_msg: str
    fail_msg: str

    def __init__(self, visible: bool, case_name: str,
                 graph_p: Optional[GraphP],
                 func_node_p: Optional[FuncNodeP],
                 source_node_p: Optional[SourceNodeP],
                 pass_msg: str, fail_msg: str,
                 max_diagnostics: int = CHECK_AST_MAX_DIAGNOSTICS_DEFAULT,
                 warning: bool = False):
        super().__init__(visible, name=case_name, warning=warning)

        self.pass_msg = pass_msg
        self.fail_msg = fail_msg

        self.graph_p = graph_p
        self.func_node_p = func_node_p
        self.source_node_p = source_node_p

        self.summary = ast_check.Summary(max_diagnostics)

        # populate sources
        self.sources = set()
        if self.graph_p is not None:
            self.sources.update(self.graph_p.spec.sources)
        if self.func_node_p is not None:
            self.sources.update(self.func_node_p.spec.sources)
        if self.source_node_p is not None:
            self.sources.update(self.source_node_p.sources)

    def check_passed(self) -> None:
        assert self.has_run

        funcs = collect_funcs(self.sources)
        self.passed = True

        # graph predicate
        if self.graph_p is not None:
            graph_root = self.graph_p.spec.identify_func(funcs)
            self.graph_p.graph_root = graph_root
            if graph_root is None:
                self.passed = False
            else:
                self.passed &= (self.graph_p.predicate)(graph_root, set())

        # node predicate (funcs)
        if self.func_node_p is not None:
            graph_root = self.func_node_p.spec.identify_func(funcs)
            self.func_node_p.graph_root = graph_root
            if graph_root is None:
                self.passed = False
            else:
                ast_check.call_node_predicate(
                    self.func_node_p.predicate,
                    self.summary,
                    graph_root,
                    set(),
                )

        # node predicate (directly on ast / source)
        if self.source_node_p is not None:
            for source_mod in self.source_node_p.sources:
                source: str = inspect.getsource(source_mod)
                source_path: PurePath = util.get_module_relpath(source_mod)
                source_root: ast.AST = ast.parse(source)
                (self.source_node_p.predicate)(
                    self.summary,
                    PurePath(source_path),
                    source_mod,
                    list(ast.walk(source_root)),
                )

        self.passed &= len(self.summary) == 0

    def run(self) -> None:
        # nothing to "run". just checks.
        self.run_post()

    def format_output(self) -> str:
        output: str = ""

        # check if we're missing any function definitions
        unresolved: Set[Tuple[ModuleType, str]] = set() # (func_def_mod, func_name)
        if self.graph_p is not None:
            if self.graph_p.graph_root is None:
                func_name = self.graph_p.spec.resolve_func_name()
                unresolved.add((self.graph_p.spec.func_def_mod, func_name))
        if self.func_node_p is not None:
            if self.func_node_p.graph_root is None:
                func_name = self.func_node_p.spec.resolve_func_name()
                unresolved.add((self.func_node_p.spec.func_def_mod, func_name))

        for (func_def_mod, func_name) in unresolved:
            func_def_path = util.get_module_relpath(func_def_mod)
            output += f"Could not find the definition of function {func_name} in file '{func_def_path}'.\n"

        if len(unresolved):
            return output
        assert len(output) == 0

        # show pass/fail status
        status = self.pass_msg if self.passed else self.fail_msg
        output += status.rstrip() + "\n"
        if self.warning:
            output += "(This check is not confident.)\n"

        # okay, but *why* ??
        if len(self.summary):
            output += "\n"
            output += "## Reasoning:\n"

        for why in self.summary.whys():
            fname: PurePath = why.fname
            msg: str = why.msg
            if isinstance(why.node_cause, ast.expr):
                line: int = why.node_cause.lineno
                output += f"- Line {line} of '{fname}': {msg}\n"
            else:
                # TODO: is/should this be this unreachable?
                output += f"- In file '{fname}': {msg}\n"

        return output

# TODO: assumes that finding recursion is desired
class CaseCheckRecursive(CaseCheckAst):
    def __init__(self, visible: bool, case_name: str,
                 func: Callable[..., Any],
                 func_name: Optional[str],
                 func_def_mod: ModuleType,
                 sources: List[ModuleType],
                 max_diagnostics: int = CHECK_AST_MAX_DIAGNOSTICS_DEFAULT,
                 warning: bool = False):
        spec: FuncSpec = FuncSpec(
            func=func, func_name=func_name,
            func_def_mod=func_def_mod, sources=sources,
        )
        graph_p: GraphP = GraphP(
            predicate=ast_check.graphp_check_recursion,
            spec=spec,
        )
        super().__init__(visible, case_name=case_name,
                         graph_p=graph_p,
                         func_node_p=None, source_node_p=None,
                         pass_msg="Found recursion!",
                         fail_msg="Did not find recursion!",
                         warning=warning)

class CaseForbidFloat(CaseCheckAst):
    def __init__(self, visible: bool, case_name: str,
                 func_node_args: Optional[FuncSpec],
                 source_node_args: Optional[SourceSpec],
                 max_diagnostics: int = CHECK_AST_MAX_DIAGNOSTICS_DEFAULT,
                 warning: bool = False):
        predicate = ast_check.nodep_forbid_float
        func_node_p = None
        source_node_p = None
        if func_node_args is not None:
            func_node_p = FuncNodeP(predicate, func_node_args)
        if source_node_args is not None:
            source_node_p = SourceNodeP(predicate, *source_node_args)
        if func_node_p is None and source_node_p is None:
            raise ValueError("One of func_node_args or source_node_args must be defined, otherwise nothing will be checked.")
        super().__init__(visible, case_name=case_name,
                         func_node_p=func_node_p,
                         source_node_p=source_node_p,
                         graph_p=None,
                         pass_msg="Did not find floating point operations, as expected.",
                         fail_msg="Unexpectedly found floating point operations.",
                         warning=warning)

class CaseForbidStrFmt(CaseCheckAst):
    def __init__(self, visible: bool, case_name: str,
                 func_node_args: Optional[FuncSpec],
                 source_node_args: Optional[SourceSpec],
                 max_diagnostics: int = CHECK_AST_MAX_DIAGNOSTICS_DEFAULT,
                 warning: bool = False):
        predicate = ast_check.nodep_forbid_str_fmt
        func_node_p = None
        source_node_p = None
        if func_node_args is not None:
            func_node_p = FuncNodeP(predicate, func_node_args)
        if source_node_args is not None:
            source_node_p = SourceNodeP(predicate, *source_node_args)
        if func_node_p is None and source_node_p is None:
            raise ValueError("One of func_node_args or source_node_args must be defined, otherwise nothing will be checked.")
        super().__init__(visible, case_name=case_name,
                         func_node_p=func_node_p, source_node_p=source_node_p,
                         graph_p=None,
                         pass_msg="Did not find string formatting, as expected.",
                         fail_msg="Unexpectedly found string formatting.",
                         warning=warning)

class DefStyle(NamedTuple):
    uses_lambda: bool
    uses_def: bool

def check_def_style(func: Callable[..., Any]) -> DefStyle:
    src: str = inspect.getsource(func)
    try:
        tree: ast.AST = ast.parse(src)
    except IndentationError:
        return DefStyle(False, False)

    uses_lambda: bool = False
    uses_def: bool = False

    if isinstance(tree, ast.Module):
        if len(tree.body) >= 1:
            node = tree.body[0]
            uses_def = isinstance(node, ast.FunctionDef)
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                uses_lambda = isinstance(node.value, ast.Lambda)

    return DefStyle(uses_lambda, uses_def)

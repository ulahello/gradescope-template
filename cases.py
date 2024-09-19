from ast_analyze import *
from core import Case, AutograderError, WHERE_THE_SUBMISSION_IS
from io_trace import Read, Write
from util import *
import ast_check
import io_trace

from typing import List, Optional, Any, Callable, Tuple, Dict, Set, TypeAlias
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

    def run_func(self,
                 func: Callable[[], Any],
                 io_queue: List[str] = [],
                 msg: str = "An exception was raised while running a student function.") -> Tuple[Any, List[Read | Write]]:
        try:
            ret, io_log = io_trace.capture(func, io_queue=io_queue)
        except Exception as e:
            raise AutograderError(e, msg)

        return ret, io_log

    def run_script(self, script: str, io_queue: List[str] = []) -> List[Read | Write]:
        _, io_log = self.run_func(
            lambda: run_script(script),
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
                  fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ) -> bool:
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

class CaseFunc(CaseIOBase):
    func: Callable[..., Any]
    args: Tuple[Any, ...]
    cmp_ret: Callable[[Any, Any], bool]
    ret_expect: Any
    ret_actual: Any
    ret_passed: Optional[bool]

    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 name: str,
                 warning: bool = False,
                 args: Tuple[Any, ...] = (),
                 ret_expect: Any = None,
                 cmp_ret: Callable[[Any, Any], bool] = cmp_ret_equ,
                 io_queue: List[str] = [],
                 io_expect: List[Read | Write] = [],
                 cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
                 fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ) -> None:
        super().__init__(visible, name=name, warning=warning,
                         io_queue=io_queue, io_expect=io_expect,
                         cmp_io=cmp_io, fmt_io=fmt_io)
        self.func = func
        self.args = args
        self.cmp_ret = cmp_ret
        self.ret_expect = ret_expect
        self.ret_actual = None
        self.ret_passed = None

    def run(self) -> None:
        try:
            self.ret_actual, self.io_actual = io_trace.capture(lambda: self.func(*self.args), self.io_queue)
        except Exception as e:
            raise AutograderError(e, "An exception was raised while running a student function.")

        self.run_post()

    def check_ret_passed(self) -> bool:
        return (self.cmp_ret)(self.ret_expect, self.ret_actual)

    def check_passed(self) -> None:
        assert self.has_run
        self.io_passed = self.check_io_passed()
        self.ret_passed = self.check_ret_passed()
        self.passed = self.io_passed and self.ret_passed

    def format_output(self) -> str:
        assert self.has_run
        assert self.ret_passed is not None, "unreachable"

        output: str = ""
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
            _, self.io_actual = io_trace.capture(lambda: run_script(self.script), self.io_queue)
        except Exception as e:
            raise AutograderError(e, "An exception was raised while running a student script.")

        self.run_post()

GraphPredicate: TypeAlias = Callable[[Func, Set[Func]], bool]
NodePredicate: TypeAlias = Callable[[ast_check.Summary, ast.AST, str], None]

class CaseCheckAst(Case):
    func: Callable[..., Any]
    func_def_path: str
    source_paths: List[str]
    sources: List[str]
    found_root: Optional[bool]

    graph_predicate: Optional[GraphPredicate]
    node_predicate: Optional[NodePredicate]
    summary: ast_check.Summary

    def __init__(self,
                 visible: bool,
                 case_name: str,
                 graph_predicate: Optional[GraphPredicate],
                 node_predicate: Optional[NodePredicate],
                 func: Callable[..., Any],
                 func_def_path: str,
                 source_paths: List[str],
                 pass_msg: str,
                 fail_msg: str,
                 warning: bool = False):
        super().__init__(visible, name=case_name, warning=warning)

        self.pass_msg = pass_msg
        self.fail_msg = fail_msg

        self.graph_predicate = graph_predicate
        self.node_predicate = node_predicate

        self.func = func
        self.func_def_path = func_def_path
        self.source_paths = source_paths

        self.found_root = None
        self.summary = ast_check.Summary()

        self.sources = []
        for path in self.source_paths:
            with open(f"{WHERE_THE_SUBMISSION_IS}/{path}", "r") as f:
                src: str = f.read()
                self.sources.append(src)

    def call_node_predicate(self, func: Func, seen: Set[Func]) -> None:
        if self.node_predicate is None:
            return
        if func in seen:
            return
        seen.add(func)

        (self.node_predicate)(self.summary, func.top_node, func.source_path)

        for called in func.calls:
            self.call_node_predicate(called, seen)

    def check_passed(self) -> None:
        assert self.has_run

        (funcs, graph_root) = collect_funcs(self.source_paths, self.sources, self.func, self.func_def_path)

        # can't do anything if we can't find the function definition
        if graph_root is None:
            self.found_root = False
            self.passed = False
            return
        else:
            self.found_root = True
            self.passed = True

        # call graph predicate
        if self.graph_predicate is not None:
            self.passed &= (self.graph_predicate)(graph_root, set())

        # call node predicate on the top level nodes of each called function
        self.call_node_predicate(graph_root, set())

        self.passed &= len(self.summary) == 0

    def run(self) -> None:
        # nothing to "run". just checks.
        self.run_post()

    def format_output(self) -> str:
        assert self.found_root is not None, "unreachable"
        if not self.found_root:
            func_name: str = self.func.__name__
            return f"Could not find the definition of function {func_name}."

        # show pass/fail status
        output: str = ""
        status = self.pass_msg if self.passed else self.fail_msg
        output += status.rstrip() + "\n"
        if self.warning:
            output += "(This check is not confident.)\n"
        output += "\n"

        # okay, but *why* ??
        for why in self.summary.whys():
            fname: str = why.fname
            msg: str = why.msg
            if isinstance(why.node_cause, ast.expr):
                line: int = why.node_cause.lineno
                output += f"- Line {line} of '{fname}': {msg}\n"
            else:
                # TODO: is/should this be this unreachable?
                output += f"- In file '{fname}': {msg}\n"

        return output

class CaseCheckRecursive(CaseCheckAst):
    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 func_def_path: str,
                 source_paths: List[str],
                 case_name: str,
                 warning: bool = False):
        super().__init__(visible, case_name=case_name,
                         graph_predicate=ast_check.check_call_graph_cycle,
                         node_predicate=None,
                         func=func, func_def_path=func_def_path,
                         source_paths=source_paths,
                         pass_msg="Found recursion!",
                         fail_msg="Did not find recursion!",
                         warning=warning)

class CaseForbidFloat(CaseCheckAst):
    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 func_def_path: str,
                 source_paths: List[str],
                 case_name: str,
                 warning: bool = False):
        super().__init__(visible, case_name=case_name,
                         node_predicate=ast_check.p_forbid_float,
                         graph_predicate=None,
                         func=func, func_def_path=func_def_path,
                         source_paths=source_paths,
                         pass_msg="Did not find floating point operations, as expected.",
                         fail_msg="Unexpectedly found floating point operations.",
                         warning=warning)

class CaseForbidStrFmt(CaseCheckAst):
    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 func_def_path: str,
                 source_paths: List[str],
                 case_name: str,
                 warning: bool = False):
        super().__init__(visible, case_name=case_name,
                         node_predicate=ast_check.p_forbid_str_fmt,
                         graph_predicate=None,
                         func=func, func_def_path=func_def_path,
                         source_paths=source_paths,
                         pass_msg="Did not find string formatting, as expected.",
                         fail_msg="Unexpectedly found string formatting.",
                         warning=warning)

def check_def_style(func: Callable[..., Any]) -> Tuple[bool, bool]:
    src: str = inspect.getsource(func)
    try:
        tree: ast.AST = ast.parse(src)
    except IndentationError:
        return (False, False)

    uses_lambda: bool = False
    uses_def: bool = False

    if isinstance(tree, ast.Module):
        if len(tree.body) >= 1:
            node = tree.body[0]
            uses_def = isinstance(node, ast.FunctionDef)
            if isinstance(node, ast.Assign):
                uses_lambda = isinstance(node.value, ast.Lambda)

    return (uses_lambda, uses_def)

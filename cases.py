from core import Case, AutograderError
from io_trace import Read, Write
from util import *
import io_trace
import recursion

from typing import List, Optional, Any, Callable, Tuple, Dict, Set
import ast
import inspect

class CaseAdHoc(Case):
    runner: Callable[["CaseAdHoc"], None]
    output: str

    def __init__(self,
                 visible: bool,
                 name: str,
                 runner: Callable[["CaseAdHoc"], None],
                 warning: bool = False) -> None:
        super().__init__(visible, name=name, warning=warning, io_queue=[], io_expect=[])
        self.io_actual = []

        self.runner = runner

        self.output = ""
        self.passed = True

    def run(self) -> None:
        (self.runner)(self)
        self.run_post()

    def run_func(self, func: Callable[[], Any], io_queue: List[str] = [], msg: str = "An exception was raised while running a student function.") -> Tuple[Any, List[Read | Write]]:
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

    def expect(self, expect: bool) -> bool:
        self.passed = self.passed and expect
        return expect

    def expect_eq(self, expect: Any, actual: Any, msg_prefix: str, cmp: Callable[[Any, Any], bool] = cmp_ret_equ) -> bool:
        assert len(msg_prefix.splitlines()) == 1

        eq: bool = cmp(expect, actual)

        if eq:
            self.print(f"{msg_prefix}: got `{repr(actual)}` as expected.")
        else:
            self.print(f"{msg_prefix}: expected `{repr(expect)}`, but got `{repr(actual)}`.")

        self.passed = self.passed and eq
        return eq

    def expect_io(self, expect: List[Read | Write], actual: List[Read | Write], silence_pass: bool = False) -> bool:
        self.has_run = True
        self.io_expect = expect
        self.io_actual = actual

        io_passed: bool = self.check_io_passed()
        self.io_passed = io_passed
        output: str = self.format_console_io_check()
        if io_passed and silence_pass:
            pass
        else:
            self.print(output, end="")

        self.has_run = False
        self.io_expect = []
        self.io_actual = []
        self.io_passed = None

        self.passed = self.passed and io_passed
        return io_passed

    def print(self, line: str, end: str = "\n") -> None:
        self.output += line + end

    def format_output(self) -> str:
        return self.output

class CaseFunc(Case):
    func: Callable[..., Any]
    args: Tuple
    cmp_ret: Callable[[Any, Any], bool]
    ret_expect: Any
    ret_actual: Any
    ret_passed: Optional[bool]

    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 name: str,
                 warning: bool = False,
                 args: Tuple = (),
                 ret_expect: Any = None,
                 cmp_ret: Callable[[Any, Any], bool] = cmp_ret_equ,
                 io_queue: List[str] = [],
                 io_expect: List[Read | Write] = []):
        super().__init__(visible, name=name, warning=warning, io_queue=io_queue, io_expect=io_expect)
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
        return self.cmp_ret(self.ret_expect, self.ret_actual)

    def check_passed(self) -> None:
        assert self.has_run
        self.io_passed = self.check_io_passed()
        self.ret_passed = self.check_ret_passed()
        self.passed = self.io_passed and self.ret_passed

    def format_output(self) -> str:
        output: str = "Return value: "
        if self.ret_passed:
            output += f"got `{repr(self.ret_actual)}` as expected.\n"
        else:
            output += f"expected `{repr(self.ret_expect)}`, but got `{repr(self.ret_actual)}`.\n"
        output += self.format_console_io_check()
        return output

class CaseScript(Case):
    def __init__(self,
                 visible: bool,
                 script: str,
                 name: str,
                 warning: bool = False,
                 io_queue: List[str] = [],
                 io_expect: List[Read | Write] = []) -> None:
        super().__init__(visible, name=name, warning=warning, io_queue=io_queue, io_expect=io_expect)
        self.script = script

    def run(self) -> None:
        try:
            _, self.io_actual = io_trace.capture(lambda: run_script(self.script), self.io_queue)
        except Exception as e:
            raise AutograderError(e, "An exception was raised while running a student script.")

        self.run_post()

# TODO: doesn't consider how import statements change items in scope (eg. doesn't understand `import module as mod; mod.func()`)
# NOTE: doesn't look at methods
class CaseCheckRecursive(Case):
    func: Callable[..., Any]
    func_def_path: str
    source_names: List[str]
    sources: List[str]

    def __init__(self,
                 visible: bool,
                 func: Callable[..., Any],
                 func_def_path: str,
                 source_names: List[str],
                 case_name: str,
                 warning: bool = False):
        super().__init__(visible, name=case_name, warning=warning, io_queue=[], io_expect=[])
        self.io_actual = []

        self.func = func
        self.func_def_path = func_def_path
        self.source_names = source_names
        self.sources = []
        for path in self.source_names:
            with open(f"submission/{path}", "r") as f:
                src: str = f.read()
                self.sources.append(src)

    def check_passed(self) -> None:
        assert self.has_run
        result: Optional[bool] = recursion.check_rec_ast_cycles(self.source_names, self.sources, self.func, self.func_def_path)
        if result is None:
            # recursion checker couldn't reasonably determine whether
            # there is recursion. so this test case should be taken
            # lightly.
            self.warning = True
            self.passed = False
        else:
            self.passed = result

    def run(self) -> None:
        # nothing to "run". just checks.
        self.run_post()

    def format_output(self) -> str:
        output: str = ""
        if self.passed:
            output += "Found recursion!\n"
        else:
            output += "Did not find recursion!\n"
        return output

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

# "Ahhh, where do I change stuff?": search for @CHANGEME

from enum import Enum
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from io import StringIO
from operator import add
from types import ModuleType
from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import ast
import importlib
import importlib.util as iu
import inspect
import io_trace as io
import itertools
import json
import os
import random
import sys
import traceback

random.seed(23)

# TODO: students may use print debugging. make sure that is useful and provides feedback??

WHERE_THE_RESULTS_GO: str = "results/results.json"
OUTPUT_FORMAT: str = "md"

class AutograderError(Exception):
    msg: str
    inner: Optional[Exception]

    def __init__(self, exception: Optional[Exception], msg: str):
        self.msg = msg
        self.inner = exception

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

def check_subclass(this: Any, subclass_of: Any):
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

def load_submission_metadata() -> Dict:
    with open("submission_metadata.json", "r") as f:
        s = f.read()
        return json.loads(s)

def cmp_ret_epsilon(expect: Any, actual: Any,
                    epsilon: float = 0.00001): # @CHANGEME (or write your own)
    if not (isinstance(actual, int) or isinstance(actual, float)):
        return False
    return abs(expect - actual) < epsilon

def cmp_ret_equ(expect: Any, actual: Any):
    return expect == actual

class Case:
    # Passed to Gradescope as either "visible" or "hidden".
    visible: bool

    # Short description of the test. Passed to Gradescope.
    name: str

    # Whether this Case's failure should be permissible.
    warning: bool

    # List of read operations to pass to stdin. Popped from index 0.
    # When the queue is empty, defers to OS as expected.
    io_queue: List[str]

    # Expected sequence of console I/O operations to observe during a test.
    io_expect: List[io.Read | io.Write]

    # Observed sequence of console I/O operations during a test.
    io_actual: Optional[List[io.Read | io.Write]]

    # `True` if the `run` method has been called and completed exactly once.
    has_run: bool

    # `True` if the Case has been `run` and all checks passed.
    passed: Optional[bool]

    # `True` if the expected I/O operations were observed.
    io_passed: Optional[bool]

    def __init__(self,
                 visible: bool,
                 name: str,
                 warning: bool,
                 io_queue: List[str],
                 io_expect: List[io.Read | io.Write]):
        self.visible = visible
        self.name = name
        self.warning = warning
        self.io_queue = io_queue
        # in case we're passed consecutive operations of the same
        # type, this will merge them (it's a pitfall otherwise)
        self.io_expect = io.normalize_log(io_expect)

        self.io_actual = None

        self.has_run = False
        self.io_passed = None

    def check_passed(self) -> None:
        assert self.has_run
        self.io_passed = self.check_io_passed()
        self.passed = self.io_passed

    def check_io_passed(self) -> bool:
        assert self.has_run
        assert self.io_expect is not None and self.io_actual is not None, "unreachable"

        if len(self.io_expect) != len(self.io_actual):
            return False

        for e, a in zip(self.io_expect, self.io_actual):
            if e.val != a.val:
                return False

        return True

    def run_post(self) -> None:
        assert not self.has_run, "case should only be run once"
        self.has_run = True
        self.check_passed()

    def run(self) -> None:
        assert False, "Case.run should be overridden to suit use case (ex. CaseFunc.run)"

    def format_console_io_check(self) -> str:
        # TODO: could display console i/o as it would appear while distinguishing reads and writes by color (should?)

        assert self.has_run
        assert self.io_actual is not None, "unreachable"

        output: str = ""

        if self.io_passed and len(self.io_expect) != 0:
            output += "All console I/O lines match.\n"

        line: int = 0
        for le, la in itertools.zip_longest(io.LineIter(self.io_expect), io.LineIter(self.io_actual)):
            line += 1

            if le is None:
                output += f"Console line {line}: too many lines\n"
                return output
            elif la is None:
                output += f"Console line {line}: want additional line(s)\n"
                return output

            for oe, oa in zip(le, la):
                if type(oe) != type(oa):
                    # mismatched read/write
                    output += f"Console line {line}: expected {oe.word()} of `{repr(oe.val)}`, but found {oa.word()} of `{repr(oa.val)}`.\n"
                    return output

                if oe.val != oa.val:
                    output += f"Console line {line} ({oe.word()}): expected `{repr(oe.val)}`, but found `{repr(oa.val)}`.\n"
                    return output

        return output

    def format_output(self) -> str:
        return self.format_console_io_check()

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
                 io_expect: List[io.Read | io.Write] = []):
        super().__init__(visible, name=name, warning=warning, io_queue=io_queue, io_expect=io_expect)
        self.func = func
        self.args = args
        self.cmp_ret = cmp_ret
        self.ret_expect = ret_expect
        self.ret_actual = None
        self.ret_passed = None

    def run(self) -> None:
        try:
            self.ret_actual, self.io_actual = io.capture(lambda: self.func(*self.args), self.io_queue)
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
                 io_expect: List[io.Read | io.Write] = []) -> None:
        super().__init__(visible, name=name, warning=warning, io_queue=io_queue, io_expect=io_expect)
        self.script = script

    def run(self) -> None:
        try:
            _, self.io_actual = io.capture(lambda: run_script(self.script), self.io_queue)
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
        result: Optional[bool] = CaseCheckRecursive.check_rec_ast_cycles(self.source_names, self.sources, self.func, self.func_def_path)
        if result is None:
            # recursion checker couldn't reasonably determine whether
            # there is recursion. so this test case should be taken
            # lightly.
            self.warning = True
            self.passed = False
        else:
            self.passed = result

    def check_rec_ast_cycles(source_names: Iterable[str], sources: Iterable[str], func: Callable[..., Any], func_def_path: str) -> Optional[bool]:
        class Func:
            name: str
            parent_def: "Func | str" # str represents module name where defined
            calls: List["Func"]
            todo_body: Optional[List[ast.AST]] # function body, awaiting being further parsed. if None, the Func is fully initialized.

            def __init__(self, name: str, parent_def: "Func | str", body: List[ast.AST]) -> None:
                self.name = name
                self.parent_def = parent_def
                self.calls = []
                self.todo_body = body

            def __hash__(self) -> int:
                return hash((self.name, self.parent_def))

            def __eq__(self, other: Any) -> bool:
                return type(self) == type(other) and hash(self) == hash(other)

            def __repr__(self) -> str:
                return f"Func{'' if self.is_fully_init() else '*'}({self.name}, {self.parent_def}, {self.calls}, {hex(id(self))})"

            def is_fully_init(self) -> bool:
                return self.todo_body is None

        def collect_funcs(mod_name: str, mod_src: str) -> Tuple[List[Func], List[Tuple[Func, Optional[str], str]]]:
            def collect_defs_shallow(parent_def: Func | str, func_body: Iterable[ast.AST]) -> Set[Func]:
                funcs: Set[Func] = set()
                for top_node in func_body:
                    funcname: Optional[str] = None
                    body: Optional[List[ast.AST]] = None

                    if isinstance(top_node, ast.FunctionDef):
                        # def foo(...):
                        funcname = top_node.name
                        body = cast(List[ast.AST], top_node.body)
                    elif isinstance(top_node, ast.Assign):
                        # foo = lambda ...
                        if len(top_node.targets) == 1:
                            [name_node] = top_node.targets
                            if isinstance(name_node, ast.Name):
                                funcname = name_node.id
                        if isinstance(top_node.value, ast.Lambda):
                            body = [top_node.value.body]

                    if funcname is not None and body is not None:
                        func: Func = Func(funcname, parent_def, body)
                        if func in funcs:
                            loc: str
                            if isinstance(func.parent_def, Func):
                                loc = f"function '{func.parent_def.name}'"
                            elif isinstance(func.parent_def, str):
                                loc = f"'{func.parent_def}'"
                            else:
                                assert False, "unreachable"
                            raise AutograderError(None, f"Function '{func.name}', defined in {loc}, has conflicting implementations. Please check that it is defined at most once.")
                        funcs.add(func)
                return funcs

            def collect_calls(body: Iterable[ast.AST]) -> Set[Tuple[Optional[str], str]]:
                calls: Set[Tuple[Optional[str], str]] = set()

                # visit all child nodes, excluding child nodes of function or lambda definitions
                for node in body:
                    for ty in [ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda]:
                        if isinstance(node, ty):
                            continue

                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            calls.add((None, node.func.id))
                        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                            calls.add((node.func.value.id, node.func.attr))
                    else:
                        calls |= collect_calls(ast.iter_child_nodes(node))

                return calls

            mod_ast: ast.AST = ast.parse(mod_src)
            assert isinstance(mod_ast, ast.Module), "probably unreachable but please notify me if hit"
            funcs: List[Func] = []
            funcs.extend(collect_defs_shallow(mod_name, mod_ast.body))
            todo_resolve: List[Tuple[Func, Optional[str], str]] = []

            found_uninit: bool = True
            while found_uninit:
                found_uninit = False
                for func in funcs:
                    if not func.is_fully_init():
                        found_uninit = True

                        assert func.todo_body is not None, "unreachable"
                        # 1) add unparsed func definitions to `funcs`
                        child_defs: Set[Func] = collect_defs_shallow(func, func.todo_body)
                        funcs.extend(child_defs)
                        # 2) collect unparsed function calls
                        raw_calls: Set[Tuple[Optional[str], str]] = collect_calls(func.todo_body)
                        # 3) place function calls into `funcs` by following parents
                        for mod, name in raw_calls:
                            if mod is not None:
                                # we don't have access to the
                                # definition of all functions in other
                                # modules (nor can we), so we resolve
                                # these later.
                                todo_resolve.append((func, mod, name))
                                continue

                            # search func defs in increasingly broad scope
                            containing: Func | str = func
                            found: bool = False
                            while not found:
                                for test_func in funcs:
                                    if containing == test_func.parent_def:
                                        assert mod is None, "unreachable"
                                        if name == test_func.name:
                                            func.calls.append(test_func)
                                            found = True
                                            break
                                if not found:
                                    if isinstance(containing, Func):
                                        containing = containing.parent_def
                                    else:
                                        # we've hit the ceiling of the parent_def chain:
                                        # the function is defined outside of our knowledge (probably in some standard module).
                                        break

                        # 4) mark func as initialized
                        func.todo_body = None

            return (funcs, todo_resolve)

        def resolve_unresolved(funcs: List[Func],
                               todo_resolve: List[Tuple[Func, Optional[str], str]]) -> None:
            while len(todo_resolve) > 0:
                func, mod, name = todo_resolve.pop()
                for test_func in funcs:
                    if f"{mod}.py" == test_func.parent_def and name == test_func.name:
                        func.calls.append(test_func)
                        break

        def check_cycle(root: Func, seen: Set[Func]) -> bool:
            for call in root.calls:
                if call in seen:
                    # found a cycle
                    return True
                seen.add(call)
                if check_cycle(call, seen):
                    return True
            return False

        # collect function call graph for entirety of sources
        funcs: List[Func] = []
        todo_resolve: List[Tuple[Func, Optional[str], str]] = []
        for mod_name, mod_src in zip(source_names, sources):
            f, t = collect_funcs(mod_name, mod_src)
            funcs.extend(f)
            todo_resolve.extend(t)

        resolve_unresolved(funcs, todo_resolve)
        assert len(todo_resolve) == 0

        # identify the function we're checking within the call graph
        graph_root: Optional[Func] = None
        for test_func in funcs:
            if test_func.parent_def == func_def_path:
                if test_func.name == func.__code__.co_name:
                    # found it!
                    graph_root = test_func

        if graph_root is None:
            # we can't analyze this if we can't find it.
            # TODO: is this unreachable given correct inputs?
            return None

        return check_cycle(graph_root, set())

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

# Summary of test cases. It is "Good" because nothing went wrong while
# loading them, eg. the submission can be tested.
class SummaryGood:
    execution_time: int

    output: str

    max_score: float
    score: float

    tests: List[Dict]
    num_visible: int
    num_passed_visible: int
    num_scored: int
    num_passed_scored: int

    def __init__(self, tests: List[Dict], max_score: float, execution_time: int) -> None:
        self.execution_time = execution_time

        self.output = ""

        self.max_score = max_score
        self.score = 0.0

        self.tests = tests
        self.num_visible = 0
        self.num_passed_visible = 0
        self.num_scored = 0
        self.num_passed_scored = 0

        self.format()

    def format(self) -> None:
        """Populate the summary with the results of the tests. Already called by constructor."""

        hidden_failing: bool = False

        for test in self.tests:
            passed: bool = test["status"] == "passed"
            visible: bool = test["visibility"] == "visible"
            scored: bool = "score" in test

            if visible:
                self.num_visible += 1
            if passed and visible:
                self.num_passed_visible += 1
            if scored:
                self.num_scored += 1
            if passed and scored:
                self.num_passed_scored += 1
            if not passed and not visible:
                    hidden_failing = True

        self.output += f"{self.num_passed_visible}/{self.num_visible} visible test(s) passed.\n"
        if hidden_failing:
            self.output += "One or more hidden tests are failing.\n"

        # compute score: all or nothing
        if self.num_passed_scored < self.num_scored:
            self.score = 0.0
        else:
            self.score = self.max_score

    def write_to_results(self) -> None:
        with open(WHERE_THE_RESULTS_GO, "w") as f:
            f.write(json.dumps({
                "score": self.score,
                "output": self.output,
                "output_format": OUTPUT_FORMAT,
                "execution_time": self.execution_time,
                "stdout_visibility": "hidden", # hidden so as to not reveal hidden test cases (if they write to stdout)
                "tests": self.tests,
            }))

# Summary of exceptions while loading test cases. It is "Bad" because
# the submission could not be tested, eg. something went wrong!
class SummaryBad:
    output_f: StringIO
    score: float
    exception: AutograderError

    def __init__(self, exception: AutograderError) -> None:
        self.output_f = StringIO("")
        self.score = 0.0
        self.exception = exception

        self.format()

    def format(self) -> None:
        """Populate the summary with the exception info. Already called by constructor."""
        print("The student submission cannot be tested!", file=self.output_f)
        print("The autograder thinks this is an issue on the student's end, but please reach out if you don't think so, or if you have questions.", file=self.output_f)
        print(file=self.output_f)

        if self.exception.inner is None:
            print(self.exception.msg, file=self.output_f)
        else:
            print("```", file=self.output_f)
            traceback.print_exception(self.exception, file=self.output_f) # @fragile: signature changed slightly in 3.10
            print("```", file=self.output_f)

    def write_to_results(self) -> None:
        with open(WHERE_THE_RESULTS_GO, "w") as f:
            f.write(json.dumps({
                "score": self.score,
                "output": self.output_f.getvalue(),
                "output_format": OUTPUT_FORMAT,
                "stdout_visibility": "visible",
            }))

def get_test_cases(metadata: Dict) -> List[Case]:
    # Submission metadata is there if you want it. If not, that's fine!

    # REMINDER: Raising any exception other than AutograderError
    # indicates an internal error (eg. bug in autograding script)!
    # AutograderErrors are presented to the student and should be
    # raised if the submission is invalid and cannot be tested.

    ############# @CHANGEME #############

    cases: List[Case] = [
    ]

    #####################################

    return cases

def run_test_cases(cases: List[Case]) -> List[Dict]:
    tests: List[Dict] = []
    for i, case in enumerate(cases):
        passed: bool
        output: str
        try:
            case.run() # @raise
            assert case.passed is not None, "unreachable"
            passed = case.passed
            output = case.format_output()
        except AutograderError as e:
            passed = False
            output_f: StringIO = StringIO("")
            print("```", file=output_f)
            traceback.print_exception(e, file=output_f) # @fragile: signature changed slightly in 3.10
            print("```", file=output_f)
            output = output_f.getvalue()

        status = "passed" if passed else "failed"
        test_info: Dict = {
            "name": case.name,
            "status": status,
            "output": f"{output}",
            "output_format": OUTPUT_FORMAT,
            "visibility": "visible" if case.visible else "hidden",
        }
        if not case.warning:
            max_score: float = 1.0
            test_info |= {
                "score": max_score if passed else 0.0,
                "max_score": max_score,
            }
        else:
            # warnings don't have scores, just pass/fail status
            pass
        tests.append(test_info)
    return tests

def main() -> None:
    metadata = load_submission_metadata()
    cases: List[Case]
    try:
        cases = get_test_cases(metadata) # @raise
    except AutograderError as e:
        # the submission can't be tested! we need to report this to the student.
        summary_bad: SummaryBad = SummaryBad(exception=e)
        summary_bad.write_to_results()
        return

    # set max_score dynamically based on however many points the assignment is worth
    max_score: float = float(metadata["assignment"]["total_points"])
    EXECUTION_TIME: int = 60

    # run the test cases!
    tests: List[Dict] = run_test_cases(cases)
    # how did they go?
    summary: SummaryGood = SummaryGood(tests, max_score=max_score, execution_time=EXECUTION_TIME)

    # write results to results.json!
    summary.write_to_results()

if __name__ == "__main__":
    io.init()
    try:
        main()
    finally:
        io.deinit()

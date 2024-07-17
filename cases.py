from core import Case, AutograderError
from util import *

from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import ast
import io_trace as io

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


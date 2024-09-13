"""Analyze standard ast to construct call graph."""

from core import *

from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import ast

# TODO: unify module resolution and make it reusable
# TODO: doesn't consider how import statements change items in scope (eg. doesn't understand `import module as mod; mod.func()`)
# NOTE: doesn't look at methods

class Func:
    name: str
    parent_def: "Func | str" # str represents module name where defined
    calls: List["Func"]
    top_node: ast.AST
    todo_body: Optional[List[ast.AST]] # function body, awaiting being further parsed. if None, the Func is fully initialized.

    def __init__(self, name: str, parent_def: "Func | str", top_node: ast.AST, body: List[ast.AST]) -> None:
        self.name = name
        self.parent_def = parent_def
        self.calls = []
        self.top_node = top_node
        self.todo_body = body

    def __hash__(self) -> int:
        return hash((self.name, self.parent_def))

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and hash(self) == hash(other)

    def __repr__(self) -> str:
        return f"Func{'' if self.is_fully_init() else '*'}({self.name}, {self.parent_def}, {self.calls}, {hex(id(self))})"

    def is_fully_init(self) -> bool:
        return self.todo_body is None

def _collect_defs_shallow(parent_def: Func | str, func_body: Iterable[ast.AST]) -> Set[Func]:
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
            func: Func = Func(funcname, parent_def, top_node, body)
            if func in funcs:
                loc: str
                if isinstance(func.parent_def, Func):
                    loc = f"function '{func.parent_def.name}'"
                elif isinstance(func.parent_def, str):
                    loc = f"'{func.parent_def}'"
                else:
                    assert False, "unreachable"
                raise AutograderError(None, f"Function '{func.name}', defined in {loc}, has conflicting implementations. Please ensure that it is defined at most once.")
            funcs.add(func)
    return funcs

def _collect_calls(body: Iterable[ast.AST]) -> Set[Tuple[Optional[str], str]]:
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
            calls |= _collect_calls(ast.iter_child_nodes(node))

    return calls

def _collect_funcs_shallow(mod_name: str, mod_src: str) -> Tuple[List[Func], List[Tuple[Func, Optional[str], str]]]:
    mod_ast: ast.AST = ast.parse(mod_src)
    assert isinstance(mod_ast, ast.Module), "probably unreachable but please notify me if hit"
    funcs: List[Func] = []
    funcs.extend(_collect_defs_shallow(mod_name, mod_ast.body))
    todo_resolve: List[Tuple[Func, Optional[str], str]] = []

    found_uninit: bool = True
    while found_uninit:
        found_uninit = False
        for func in funcs:
            if not func.is_fully_init():
                found_uninit = True

                assert func.todo_body is not None, "unreachable"
                # 1) add unparsed func definitions to `funcs`
                child_defs: Set[Func] = _collect_defs_shallow(func, func.todo_body)
                funcs.extend(child_defs)
                # 2) collect unparsed function calls
                raw_calls: Set[Tuple[Optional[str], str]] = _collect_calls(func.todo_body)
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
                            # NOTE: this is also "module resolution"
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

def _resolve_unresolved(funcs: List[Func],
                       todo_resolve: List[Tuple[Func, Optional[str], str]]) -> None:
    while len(todo_resolve) > 0:
        func, mod, name = todo_resolve.pop()
        for test_func in funcs:
            # NOTE: this is where (super basic) "module resolution" happens
            if f"{mod}.py" == test_func.parent_def and name == test_func.name:
                func.calls.append(test_func)
                break

def collect_funcs(source_names: Iterable[str], sources: Iterable[str], func: Callable[..., Any], func_def_path: str) -> Tuple[List[Func], Optional[Func]]:
    # collect function call graph for entirety of sources
    funcs: List[Func] = []
    todo_resolve: List[Tuple[Func, Optional[str], str]] = []
    for mod_name, mod_src in zip(source_names, sources):
        f, t = _collect_funcs_shallow(mod_name, mod_src)
        funcs.extend(f)
        todo_resolve.extend(t)

    _resolve_unresolved(funcs, todo_resolve)
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
        pass

    return (funcs, graph_root)

def check_mod_item_eq(to_test: Iterable[Tuple[Optional[str], str]],
                      mod: Optional[str], item: str) -> bool:
    for test_mod, test_item in to_test:
        # TODO: consider import statement side effects
        eq: bool = test_mod == mod and test_item == item
        if eq:
            return True
    return False

def unpack_attr(node: ast.Attribute | ast.Name) -> Tuple[Optional[str], str]:
    name: Optional[str] = None
    mod: Optional[str] = None
    if isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, ast.Attribute):
        name = node.attr
        if isinstance(node.value, ast.Name):
            mod = node.value.id
    else:
        assert False, "unreachable"
    return (mod, name)

def check_mod_eq(to_test: Iterable[str],
                 node: ast.Attribute | ast.Name) -> bool:
    (mod, _) = unpack_attr(node)
    for test_mod in to_test:
        if test_mod == mod:
            return True
    return False

def check_var_eq(to_test: Iterable[Tuple[Optional[str], str]],
                 node: ast.Attribute | ast.Name) -> bool:
    (mod, name) = unpack_attr(node)
    return check_mod_item_eq(to_test, mod, name)

def check_call_eq(to_test: Iterable[Tuple[Optional[str], str]],
                  node: ast.Call) -> Optional[bool]:
    if isinstance(node.func, ast.Name) or isinstance(node.func, ast.Attribute):
        return check_var_eq(to_test, node.func)
    return None

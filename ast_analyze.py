"""Analyze standard ast to construct call graph."""

from core import AutograderError
import util

from pathlib import PurePath
from types import ModuleType
from typing import List, Optional, Any, Callable, Tuple, Set, Iterable, Generator, cast
import ast
import inspect

# NOTE: doesn't look at methods

class Func:
    name: str
    source_path: PurePath
    parent_def: "Func | ModuleType"
    defines: List["Func"]
    calls: List["Func"]
    top_node: ast.AST
    todo_body: Optional[List[ast.AST]] # function body, awaiting being further parsed. if None, the Func is fully initialized.
    body: Tuple[ast.AST, ...]

    def __init__(self, name: str, parent_def: "Func | ModuleType",
                 top_node: ast.AST, body: List[ast.AST]) -> None:
        source_path: PurePath
        if isinstance(parent_def, Func):
            source_path = parent_def.source_path
        elif isinstance(parent_def, ModuleType):
            source_path = util.get_module_relpath(parent_def)
        else:
            assert False, "unreachable"

        self.name = name
        self.source_path = source_path
        self.parent_def = parent_def
        self.defines = []
        self.calls = []
        self.top_node = top_node
        self.body = tuple(body)
        self.todo_body = body

    def __hash__(self) -> int:
        return hash((self.name, self.parent_def))

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and hash(self) == hash(other)

    def __repr__(self) -> str:
        return f"Func{'' if self.is_fully_init() else '*'}({self.name}, {self.parent_def}, {self.calls}, {hex(id(self))})"

    def is_fully_init(self) -> bool:
        return self.todo_body is None

    def display_parent_def(self) -> str:
        if isinstance(self.parent_def, Func):
            return f"function '{self.parent_def.name}' of '{self.source_path}'"
        elif isinstance(self.parent_def, ModuleType):
            return f"'{self.source_path}'"
        else:
            assert False, "unreachable"

    def containing_module(self) -> ModuleType:
        func: Func | ModuleType = self
        while isinstance(func, Func):
            func = func.parent_def
        assert isinstance(func, ModuleType)
        return func

def is_node_executed(node: ast.AST) -> bool:
    # the child nodes of the following types are not executed
    # until the function is called or class is used (etc)
    for ty in [ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda]:
        if isinstance(node, ty):
            return False
    return True

def iter_nodes_executed(body: Iterable[ast.AST]) -> Generator[ast.AST, ast.AST, None]:
    """Iterate the flat list of nodes to yield those that may be
    executed directly (eg. excluding nodes in function or class
    definitions)."""

    for node in body:
        if is_node_executed(node):
            yield node
    return None

def walk_nodes_executed(body: Iterable[ast.AST]) -> Generator[ast.AST, ast.AST, None]:
    """Recursively walk the list of nodes to yield those that may be
    executed directly (eg. excluding nodes in function or class
    definitions). This will traverse the subtrees contained by the top
    level nodes, unlike `iter_nodes_executed`, which only yields
    top-level nodes."""

    for child in iter_nodes_executed(body):
        if is_node_executed(child):
            yield child
            yield from walk_nodes_executed(ast.iter_child_nodes(child))

def collect_funcs(sources: Iterable[ModuleType]) -> List[Func]:
    # pass 1: collect definitions
    funcs: List[Func] = []
    todo_resolve: List[Tuple[Func, Optional[str], str]] = []
    for module in sources:
        mod_src = inspect.getsource(module)
        f, t = _collect_funcs_without_calls(module, ast.parse(mod_src))
        funcs.extend(f)
        todo_resolve.extend(t)

    # pass 2: resolve calls
    _resolve_calls(funcs, todo_resolve)
    assert len(todo_resolve) == 0

    return funcs

def identify_func(funcs: List[Func],
                  func_def_mod: ModuleType, func: Callable[..., Any],
                  func_name: Optional[str] = None) -> Optional[Func]:
    if func_name is None:
        func_name = func.__code__.co_name
    for test_func in funcs:
        if check_mod_func_eq(func_def_mod, func, (None, test_func.name)):
            return test_func
    return None

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

def get_mod_item(module: ModuleType, query: Tuple[Optional[str], str]) -> Optional[Any]:
    qmod, qname = query
    try:
        if qmod is None:
            test = getattr(module, qname)
        else:
            parent = getattr(module, qmod)
            test = getattr(parent, qname)
    except AttributeError:
        return None
    return test

def get_mod_func(module: ModuleType, query: Tuple[Optional[str], str]) -> Optional[Callable[..., Any]]:
    test = get_mod_item(module, query)
    if not callable(test):
        return None
    return cast(Callable[..., Any], test)

def check_mod_item_eq(module: ModuleType, spec: Any, query: Tuple[Optional[str], str]) -> bool:
    return spec is get_mod_item(module, query)

def check_mod_func_eq(module: ModuleType, spec: Callable[..., Any], query: Tuple[Optional[str], str]) -> bool:
    # TODO: handling builtin functions by special casing feels hacky (am i forgetting another case???)
    mod, name = query
    by_lookup: bool = spec is get_mod_func(module, query)
    by_builtin: bool = mod is None and inspect.isbuiltin(spec) and name == spec.__name__
    by_ctor: bool = mod is None and inspect.isclass(spec) and name == spec.__name__
    return by_lookup or by_builtin or by_ctor

def check_mod_eq(module: ModuleType, spec: ModuleType, query: str) -> bool:
    try:
        test = getattr(module, query)
    except AttributeError:
        return False
    return spec is test

###### internals

def _collect_child_defs_shallow(parent_def: Func | ModuleType, func_body: Iterable[ast.AST]) -> Set[Func]:
    funcs: Set[Func] = set()
    for top_node in func_body:
        funcname: Optional[str] = None
        body: Optional[List[ast.AST]] = None

        if isinstance(top_node, ast.FunctionDef):
            # def foo(...):
            funcname = top_node.name
            body = cast(List[ast.AST], top_node.body)

        elif isinstance(top_node, (ast.Assign, ast.AnnAssign)):
            # foo = lambda ...

            # extract body
            if isinstance(top_node.value, ast.Lambda):
                body = [top_node.value.body]

            # extract name
            name_node: Optional[ast.AST] = None
            if isinstance(top_node, ast.Assign):
                if len(top_node.targets) == 1:
                    [name_node] = top_node.targets
            elif isinstance(top_node, ast.AnnAssign):
                # foo: Callable[...] = lambda ...
                name_node = top_node.target
            if isinstance(name_node, ast.Name):
                funcname = name_node.id

        elif isinstance(top_node, ast.AnnAssign):
            # foo: Callable[...] = lambda ...
            name_node = top_node.target
            if isinstance(name_node, ast.Name):
                funcname = name_node.id
            if isinstance(top_node.value, ast.Lambda):
                body = [top_node.value.body]

        if funcname is not None and body is not None:
            func: Func = Func(funcname, parent_def, top_node, body)
            if func in funcs:
                raise AutograderError(None, f"Function '{func.name}', defined in {func.display_parent_def()}, has conflicting implementations. Please ensure that it is defined at most once.")
            funcs.add(func)

    return funcs

def _collect_calls(body: Iterable[ast.AST]) -> Set[Tuple[Optional[str], str]]:
    calls: Set[Tuple[Optional[str], str]] = set()

    # visit all child nodes, excluding child nodes of function or lambda definitions
    for node in iter_nodes_executed(body):
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            spec = unpack_attr(node.func)
            calls.add(spec)
        calls |= _collect_calls(ast.iter_child_nodes(node))

    return calls

def _collect_funcs_without_calls(module: ModuleType, mod_ast: ast.AST) -> Tuple[List[Func], List[Tuple[Func, Optional[str], str]]]:
    assert isinstance(mod_ast, ast.Module), "probably unreachable but please notify me if hit"

    funcs: List[Func] = []
    todo_resolve: List[Tuple[Func, Optional[str], str]] = []

    graph_edge = _collect_child_defs_shallow(module, mod_ast.body)
    next_graph_edge: Set[Func] = set()
    while len(graph_edge):
        for func in graph_edge:
            assert func.todo_body is not None, "unreachable"

            # 1) add unparsed func definitions to next graph edge
            child_defs: Set[Func] = _collect_child_defs_shallow(func, func.todo_body)
            func.defines.extend(child_defs)
            next_graph_edge.update(child_defs)

            # 2) collect unparsed function calls
            raw_calls: Set[Tuple[Optional[str], str]] = _collect_calls(func.todo_body)
            todo_resolve.extend(map(lambda call: (func, *call), raw_calls))

        funcs.extend(graph_edge)
        graph_edge, next_graph_edge = next_graph_edge, graph_edge
        next_graph_edge.clear()

    return (funcs, todo_resolve)

def _lookup_call(funcs: List[Func], func: Func, mod: Optional[str], name: str) -> Optional[Func]:
    # the called function is defined in...
    if mod is None:
        # case 1: the current function
        for defines in func.defines:
            if defines.name == name:
                return defines

        # case 2: a parent function
        parent = func.parent_def
        while isinstance(parent, Func):
            for defines in parent.defines:
                if defines.name == name:
                    return defines
            parent = parent.parent_def
        assert isinstance(parent, ModuleType)
    else:
        parent = func.containing_module()

    # try to find a Func that corresponds to `target`
    target: Optional[Callable[..., Any]] = get_mod_func(parent, (mod, name))
    if target is None:
        return None

    for test in funcs:
        if not isinstance(test.parent_def, ModuleType):
            # not defined top-level
            continue

        if getattr(test.parent_def, test.name) == target:
            return test

    # it could be a function from a module we weren't told about
    # (ex. standard library, supposing it is not passed)
    return None

def _resolve_calls(funcs: List[Func], todo_resolve: List[Tuple[Func, Optional[str], str]]) -> None:
    while len(todo_resolve) > 0:
        func, mod, name = todo_resolve.pop()
        call = _lookup_call(funcs, func, mod, name)
        if call is not None:
            func.calls.append(call)

    # mark all funcs as initialized, now that calls are resolved
    for func in funcs:
        func.todo_body = None

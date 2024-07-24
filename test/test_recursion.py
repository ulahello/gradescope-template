import sys
sys.path.append("../")

import recursion
import test_recursion_ext

func0 = lambda x: 0

def func1(x):
    return 0

def func2(x):
    inner = lambda x: 0 if x == 0 else inner(x - 1)
    return inner(x)

def func3(x):
    def inner(x):
        if x == 0:
            return 0
        return inner(x - 1)
    return test_recursion_ext.hehe(inner(x))

def func4(x):
    if x == 0:
        return 0
    return func4(x - 1)

def func5(x):
    return func4(x)

sources = []
source_names = ["test_recursion.py", "test_recursion_ext.py"]
for path in source_names:
    with open(path, "r") as f:
        sources.append(f.read())

assert not recursion.check_rec_ast_cycles(source_names, sources, func0, "test_recursion.py")
assert not recursion.check_rec_ast_cycles(source_names, sources, func1, "test_recursion.py")
assert recursion.check_rec_ast_cycles(source_names, sources, func2, "test_recursion.py")
assert recursion.check_rec_ast_cycles(source_names, sources, func3, "test_recursion.py")
assert recursion.check_rec_ast_cycles(source_names, sources, func4, "test_recursion.py")
assert recursion.check_rec_ast_cycles(source_names, sources, func5, "test_recursion.py")

print("OK")

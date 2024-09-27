from test_recursion import *

import cases

def main() -> None:
    for func_name, expect in [
            ("func0", (True, False)),
            ("func0b", (True, False)),
            ("func1", (False, True)),
            ("func2", (False, True)),
            ("func2b", (False, True)),
            ("func3", (False, True)),
            ("func4", (False, True)),
            ("func5", (False, True)),
       ]:
        func = eval(func_name)
        assert cases.check_def_style(func) == expect, f"{func_name} should yield {expect}"

    print("OK")

if __name__ == "__main__":
    main()

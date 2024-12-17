import sys

import test_check_def_style
import test_forbid_float
import test_forbid_str
import test_recursion
import test_util

if __name__ == "__main__":
    for log, mod in [
            ("Def style", test_check_def_style),
            ("Float ops", test_forbid_float),
            ("String formatting", test_forbid_str),
            ("Recursion", test_recursion),
            ("util", test_util),
    ]:
        print(f"{log}...", end="")
        sys.stdout.flush()
        mod.main()

    print("All tests OK!")

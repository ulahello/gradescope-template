import sys
sys.path.append("../")

from util import *

from typing import List, Callable, Optional, Any
assert cmp_ret_seq_freq([2, 2, 3], [2, 3, 2])
assert not cmp_ret_seq_freq([2, 2, 3], [2, 0, 2])
assert not cmp_ret_seq_freq([2, 2, 3], [2, 2])
assert not cmp_ret_seq_freq([2, 2, 3], [2, 3])
assert cmp_ret_seq_freq([["foo"], ["bar"], ["bar"]], [["bar"], ["bar"], ["foo"]])
assert not cmp_ret_seq_freq([["foo"], ["bar"], ["bar"]], [["bar"], ["foo"]])

print("OK")

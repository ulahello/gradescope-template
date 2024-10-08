# Search this repository for @CHANGEME to find where code might need to be tweaked or added.

from cases import *
from core import *
from io_trace import Read, Write
from pipeline import *
from util import *
import ast_check
import io_trace

from typing import Dict, List, Any, Optional, Callable
import random

def get_test_cases(metadata: Dict[str, Any]) -> List[Case]:
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

if __name__ == "__main__":
    io_trace.init()
    try:
        random.seed(23)
        autograder_main(get_test_cases)
    finally:
        io_trace.deinit()

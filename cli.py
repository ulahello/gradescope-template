from core import JsonMetadata, Case, autograder_main, EXIT_SUCCESS
from typing import List, Callable, Optional, NoReturn
import argparse
import io_trace
import random

# TODO: two mains is confusing

def main(get_test_cases: Callable[[JsonMetadata], List[Case]], rng_seed: int = 23) -> NoReturn:
    parser = argparse.ArgumentParser(
        description="""
        Gradescope autograder for Python
        """,
    )
    parser.add_argument("--summary", action="store_true", help="print a summary of tests after writing to results.json")
    args = parser.parse_args()

    # run the autograder
    exit_code: int = 0

    io_trace.init()
    try:
        random.seed(rng_seed)
        exit_code = autograder_main(get_test_cases, args.summary)
    finally:
        io_trace.deinit()

    if args.summary:
        exit(exit_code)

    exit(EXIT_SUCCESS)

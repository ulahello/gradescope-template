from core import JsonMetadata, Case, autograder_main
from typing import List, Callable, Optional
import argparse
import io_trace
import random

# TODO: two mains is confusing

def main(get_test_cases: Callable[[JsonMetadata], List[Case]], rng_seed: int = 23) -> None:
    parser = argparse.ArgumentParser(
        description="""
        Gradescope autograder for Python
        """,
    )
    parser.add_argument("--summary", action="store_true", help="print a summary of tests after writing to results.json")
    args = parser.parse_args()

    # run the autograder
    io_trace.init()
    try:
        random.seed(rng_seed)
        autograder_main(get_test_cases, args.summary)
    finally:
        io_trace.deinit()

    # summarize the results

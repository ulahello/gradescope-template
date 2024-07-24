from io import StringIO
from typing import List, Optional, Any, Callable, Tuple, Dict, Set, Sequence, Iterable, cast
import io_trace as io
import itertools
import json
import traceback

# TODO: students may use print debugging. make sure that is useful and provides feedback??
# TODO: the quantity of input to a console interaction may be uncouth to represent as a case title, and instead the entire interaction should be displayed to the student (instead of just "all lines match" or something)
# TODO: script should not be able to hang if exact console I/O interaction spelled out (possible to see that it's doing a read when we expected end?)

WHERE_THE_RESULTS_GO: str = "results/results.json"
OUTPUT_FORMAT: str = "md"

class AutograderError(Exception):
    msg: str
    inner: Optional[Exception]

    def __init__(self, exception: Optional[Exception], msg: str):
        self.msg = msg
        self.inner = exception

class Case:
    # Passed to Gradescope as either "visible" or "hidden".
    visible: bool

    # Short description of the test. Passed to Gradescope.
    name: str

    # Whether this Case's failure should be permissible.
    warning: bool

    # List of read operations to pass to stdin. Popped from index 0.
    # When the queue is empty, defers to OS as expected.
    io_queue: List[str]

    # Expected sequence of console I/O operations to observe during a test.
    io_expect: List[io.Read | io.Write]

    # Observed sequence of console I/O operations during a test.
    io_actual: Optional[List[io.Read | io.Write]]

    # `True` if the `run` method has been called and completed exactly once.
    has_run: bool

    # `True` if the Case has been `run` and all checks passed.
    passed: Optional[bool]

    # `True` if the expected I/O operations were observed.
    io_passed: Optional[bool]

    def __init__(self,
                 visible: bool,
                 name: str,
                 warning: bool,
                 io_queue: List[str],
                 io_expect: List[io.Read | io.Write]):
        self.visible = visible
        self.name = name
        self.warning = warning
        self.io_queue = io_queue
        # in case we're passed consecutive operations of the same
        # type, this will merge them (it's a pitfall otherwise)
        self.io_expect = io.normalize_log(io_expect)

        self.io_actual = None

        self.has_run = False
        self.io_passed = None

    def check_passed(self) -> None:
        assert self.has_run
        self.io_passed = self.check_io_passed()
        self.passed = self.io_passed

    def check_io_passed(self) -> bool:
        assert self.has_run
        assert self.io_expect is not None and self.io_actual is not None, "unreachable"

        if len(self.io_expect) != len(self.io_actual):
            return False

        for e, a in zip(self.io_expect, self.io_actual):
            if e.val != a.val:
                return False

        return True

    def run_post(self) -> None:
        assert not self.has_run, "case should only be run once"
        self.has_run = True
        self.check_passed()

    def run(self) -> None:
        assert False, "Case.run should be overridden to suit use case (ex. CaseFunc.run)"

    def format_console_io_check(self) -> str:
        # TODO: could display console i/o as it would appear while distinguishing reads and writes by color (should?)

        assert self.has_run
        assert self.io_actual is not None, "unreachable"

        output: str = ""

        if self.io_passed and len(self.io_expect) != 0:
            output += "All console I/O lines match.\n"

        line: int = 0
        for le, la in itertools.zip_longest(io.LineIter(self.io_expect), io.LineIter(self.io_actual)):
            line += 1

            if le is None:
                output += f"Console line {line}: too many lines\n"
                return output
            elif la is None:
                output += f"Console line {line}: want additional line(s)\n"
                return output

            for oe, oa in zip(le, la):
                if type(oe) != type(oa):
                    # mismatched read/write
                    output += f"Console line {line}: expected {oe.word()} of `{repr(oe.val)}`, but found {oa.word()} of `{repr(oa.val)}`.\n"
                    return output

                if oe.val != oa.val:
                    output += f"Console line {line} ({oe.word()}): expected `{repr(oe.val)}`, but found `{repr(oa.val)}`.\n"
                    return output

        return output

    def format_output(self) -> str:
        return self.format_console_io_check()

# Summary of test cases. It is "Good" because nothing went wrong while
# loading them, eg. the submission can be tested.
class SummaryGood:
    execution_time: int

    output: str

    max_score: float
    score: float

    tests: List[Dict]
    num_visible: int
    num_passed_visible: int
    num_scored: int
    num_passed_scored: int

    def __init__(self, tests: List[Dict], max_score: float, execution_time: int) -> None:
        self.execution_time = execution_time

        self.output = ""

        self.max_score = max_score
        self.score = 0.0

        self.tests = tests
        self.num_visible = 0
        self.num_passed_visible = 0
        self.num_scored = 0
        self.num_passed_scored = 0

        self.format()

    def format(self) -> None:
        """Populate the summary with the results of the tests. Already called by constructor."""

        hidden_failing: bool = False

        for test in self.tests:
            passed: bool = test["status"] == "passed"
            visible: bool = test["visibility"] == "visible"
            scored: bool = "score" in test

            if visible:
                self.num_visible += 1
            if passed and visible:
                self.num_passed_visible += 1
            if scored:
                self.num_scored += 1
            if passed and scored:
                self.num_passed_scored += 1
            if not passed and not visible:
                    hidden_failing = True

        self.output += f"{self.num_passed_visible}/{self.num_visible} visible test(s) passed.\n"
        if hidden_failing:
            self.output += "One or more hidden tests are failing.\n"

        # compute score: all or nothing
        if self.num_passed_scored < self.num_scored:
            self.score = 0.0
        else:
            self.score = self.max_score

    def write_to_results(self) -> None:
        with open(WHERE_THE_RESULTS_GO, "w") as f:
            f.write(json.dumps({
                "score": self.score,
                "output": self.output,
                "output_format": OUTPUT_FORMAT,
                "execution_time": self.execution_time,
                "stdout_visibility": "hidden", # hidden so as to not reveal hidden test cases (if they write to stdout)
                "tests": self.tests,
            }))

# Summary of exceptions while loading test cases. It is "Bad" because
# the submission could not be tested, eg. something went wrong!
class SummaryBad:
    output_f: StringIO
    score: float
    exception: AutograderError

    def __init__(self, exception: AutograderError) -> None:
        self.output_f = StringIO("")
        self.score = 0.0
        self.exception = exception

        self.format()

    def format(self) -> None:
        """Populate the summary with the exception info. Already called by constructor."""
        print("The student submission cannot be tested!", file=self.output_f)
        print("The autograder thinks this is an issue on the student's end, but please reach out if you don't think so, or if you have questions.", file=self.output_f)
        print(file=self.output_f)

        if self.exception.inner is None:
            print(self.exception.msg, file=self.output_f)
        else:
            print("```", file=self.output_f)
            traceback.print_exception(self.exception, file=self.output_f) # @fragile: signature changed slightly in 3.10
            print("```", file=self.output_f)

    def write_to_results(self) -> None:
        with open(WHERE_THE_RESULTS_GO, "w") as f:
            f.write(json.dumps({
                "score": self.score,
                "output": self.output_f.getvalue(),
                "output_format": OUTPUT_FORMAT,
                "stdout_visibility": "visible",
            }))

def run_test_cases(cases: List[Case]) -> List[Dict]:
    tests: List[Dict] = []
    for i, case in enumerate(cases):
        passed: bool
        output: str
        try:
            case.run() # @raise
            assert case.passed is not None, "unreachable"
            passed = case.passed
            output = case.format_output()
        except AutograderError as e:
            passed = False
            output_f: StringIO = StringIO("")
            if e.inner is None:
                print(e.msg, file=output_f)
            else:
                print("```", file=output_f)
                traceback.print_exception(e, file=output_f) # @fragile: signature changed slightly in 3.10
                print("```", file=output_f)
            output = output_f.getvalue()

        status = "passed" if passed else "failed"
        test_info: Dict = {
            "name": case.name,
            "status": status,
            "output": f"{output}",
            "output_format": OUTPUT_FORMAT,
            "visibility": "visible" if case.visible else "hidden",
        }
        if not case.warning:
            max_score: float = 1.0
            test_info |= {
                "score": max_score if passed else 0.0,
                "max_score": max_score,
            }
        else:
            # warnings don't have scores, just pass/fail status
            pass
        tests.append(test_info)
    return tests


def load_submission_metadata() -> Dict:
    with open("submission_metadata.json", "r") as f:
        s = f.read()
        metadata: Dict = json.loads(s)
        return metadata

def autograder_main(get_test_cases: Callable[[Dict], List[Case]]) -> None:
    metadata = load_submission_metadata()
    cases: List[Case]
    try:
        cases = get_test_cases(metadata) # @raise
    except AutograderError as e:
        # the submission can't be tested! we need to report this to the student.
        summary_bad: SummaryBad = SummaryBad(exception=e)
        summary_bad.write_to_results()
        return

    # set max_score dynamically based on however many points the assignment is worth
    max_score: float = float(metadata["assignment"]["total_points"])
    EXECUTION_TIME: int = 60

    # run the test cases!
    tests: List[Dict] = run_test_cases(cases)
    # how did they go?
    summary: SummaryGood = SummaryGood(tests, max_score=max_score, execution_time=EXECUTION_TIME)

    # write results to results.json!
    summary.write_to_results()

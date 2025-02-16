from io import StringIO
from pathlib import PurePath
from traceback import FrameSummary
from typing import Union, Literal, List, Any, Optional, Callable, Tuple, Dict, Set, Sequence, Iterable, TypedDict, TypeAlias, cast
import inspect
import json
import os
import traceback

# TODO: script should not be able to hang if exact console I/O interaction spelled out (possible to see that it's doing a read when we expected end?)

# TODOO: currently, crashes must be reported by students for them to
# be noticed. their incentive is to get their homework in, so they'll
# probably resubmit until it does not crash. however, the goal is to
# make sure that as many crashes as possible are reported. it might be
# better to do automated crash reporting so the burden isn't on
# students AND we catch more bugs.

WHERE_THE_RESULTS_GO: str = "results/results.json"
WHERE_THE_SUBMISSION_IS: str = "submission"
OUTPUT_FORMAT: "JsonOutputFormat" = "md"

EXIT_SUCCESS: int = 0
EXIT_FAILURE: int = 1

JsonOutputFormat: TypeAlias = Union[
    Literal["text"],
    Literal["html"],
    Literal["simple_format"],
    Literal["md"],
    Literal["ansi"],
]

JsonStatus: TypeAlias = Union[
    Literal["passed"],
    Literal["failed"],
]

JsonVisibility: TypeAlias = Union[
    Literal["visible"],
    Literal["hidden"],
    Literal["after_due_date"],
]

JsonSummary: TypedDict = TypedDict(
    "JsonSummary",
    {
        "score": float,
        "execution_time": int,
        "output": str,
        "output_format": JsonOutputFormat,
        "test_name_format": JsonOutputFormat,
        "visibility": JsonVisibility,
        "stdout_visibility": JsonVisibility,
        "extra_data": Dict[str, Any],
        "tests": List["JsonTestCase"],
    },
    total=False,
)

JsonTestCase: TypedDict = TypedDict(
    "JsonTestCase",
    {
        "score": float,
        "max_score": float,
        "status": JsonStatus,
        "name": str,
        "name_format": str,
        "number": str,
        "output": str,
        "output_format": JsonOutputFormat,
        "tags": List[str],
        "visibility": str,
        "extra_data": Dict[str, Any],
    },
    total=False,
)

JsonMetadataAssignment: TypedDict = TypedDict(
    "JsonMetadataAssignment",
    {
        "due_date": str,
        "group_size": int,
        "group_submission": bool,
        "id": int,
        "course_id": int,
        "late_due_date": Optional[str],
        "release_date": str,
        "title": str,
        "total_points": float,
    },
)

JsonMetadataUser: TypedDict = TypedDict(
    "JsonMetadataUser",
    {
        "email": str,
        "id": int,
        "name": str,
    },
)

JsonMetadataPrevious: TypedDict = TypedDict(
    "JsonMetadataPrevious",
    {
        "submission_time": str,
        "score": float,
        "results": "JsonMetadata",
    },
)

JsonMetadata: TypedDict = TypedDict(
    "JsonMetadata",
    {
        "id": int,
        "created_at": str,
        "assignment": JsonMetadataAssignment,
        "submission_method": Literal["upload"] | Literal["GitHub"] | Literal["BitBucket"],
        "users": List[JsonMetadataUser],
        "previous_submissions": List[JsonMetadataPrevious],
    },
)

class AutograderError(Exception):
    msg: str
    inner: Optional[Exception]

    def __init__(self, exception: Optional[Exception], msg: str):
        self.msg = msg
        self.inner = exception

def format_traceback(payload: Exception) -> str:
    def frame_predicate(filename: str) -> bool:
        path = PurePath(filename)
        parent_dir = os.path.basename(path.parent)
        return parent_dir == WHERE_THE_SUBMISSION_IS

    def filter_tb(exc: BaseException, seen: Set[int]) -> None:
        if id(exc) in seen:
            return
        seen.add(id(exc))

        tb = exc.__traceback__ # https://peps.python.org/pep-3134/
        while tb is not None:
            tb_info = inspect.getframeinfo(tb)
            tb = tb.tb_next # https://docs.python.org/3/reference/datamodel.html#traceback.tb_next
            # TODO: absolute path of student submission pulls back curtain on gradescope directory hierarchy
            if frame_predicate(tb_info.filename):
                break
            else:
                exc.__traceback__ = tb

        cause = exc.__cause__
        context = exc.__context__
        if cause is not None:
            filter_tb(cause, seen)
        if context is not None:
            filter_tb(context, seen)

    f = StringIO("")

    # don't want to print an AutograderError.
    # keep getting at the inner exception.
    exception: Optional[Exception] = payload
    while type(exception) == AutograderError:
        print(exception.msg, file=f)
        exception = exception.inner

    if exception is not None:
        filter_tb(exception, set())

        print("```text", file=f)
        for line in traceback.format_exception(exception): # @fragile: signature changed slightly in 3.10
            print(line, end="", file=f)
        print("```", file=f)

    return f.getvalue()

class Case:
    # Passed to Gradescope as either "visible" or "hidden".
    visible: bool

    # Short description of the test. Passed to Gradescope.
    name: str

    # Whether this Case's failure should be permissible.
    warning: bool

    # `True` if the `run` method has been called and completed exactly once.
    has_run: bool

    # `True` if the Case has been `run` and all checks passed.
    passed: Optional[bool]

    def __init__(self,
                 visible: bool,
                 name: str,
                 warning: bool) -> None:
        self.visible = visible
        self.name = name
        self.warning = warning
        self.has_run = False
        self.passed = None

    def check_passed(self) -> None:
        assert False, "Case.check_passed should be overridden to suit use case"

    def run_post(self) -> None:
        assert not self.has_run, "case should only be run once"
        self.has_run = True
        self.check_passed()

    def run(self) -> None:
        assert False, "Case.run should be overridden to suit use case (ex. CaseFunc.run)"

    def format_output(self) -> str:
        assert False, "Case.format_output should be overridden to suit use case"

# Summary of test cases. It is "Good" because nothing went wrong while
# loading them, eg. the submission can be tested.
class SummaryGood:
    output: str

    max_score: float
    score: float

    tests: List[JsonTestCase]
    num_visible: int
    num_passed_visible: int
    num_scored: int
    num_passed_scored: int

    def __init__(self, tests: List[JsonTestCase], max_score: float) -> None:
        self.output = ""

        self.max_score = max_score
        self.score = 0.0

        self.tests = tests
        self.num_visible = 0
        self.num_passed_visible = 0
        self.num_scored = 0
        self.num_passed_scored = 0

        self._format()

    def all_passed(self) -> bool:
        return self.num_passed_scored == self.num_scored

    def _format(self) -> None:
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

        all_passed: bool = self.all_passed()
        assert self.num_passed_scored <= self.num_scored, "unreachable"

        if all_passed:
            self.output += "# All tests pass!\n"
        else:
            self.output += "# Some tests are failing!\n"
            if hidden_failing:
                self.output += "One or more hidden tests are failing.\n"

                # also add a test case that indicates this for extra clarity
                self.tests.append({
                    "name": "Hidden tests failing!",
                    "status": "failed",
                    "output": "Double-check that your submission is correctly handling all valid inputs.\n",
                    "output_format": OUTPUT_FORMAT,
                    "visibility": "visible",
                })

        self.output += f"{self.num_passed_visible}/{self.num_visible} visible tests passed.\n"

        # compute score: all or nothing
        if all_passed:
            self.score = self.max_score
        else:
            self.score = 0.0

    def get_summary(self) -> JsonSummary:
        return {
            "score": self.score,
            "output": self.output,
            "output_format": OUTPUT_FORMAT,
            "stdout_visibility": "hidden", # hidden so as to not reveal hidden test cases (if they write to stdout)
            "tests": self.tests,
        }

    def report(self, should_print_summary: bool) -> None:
        summary = self.get_summary()
        write_summary(summary)
        if should_print_summary:
            print_summary(summary)

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

        self._format()

    def _format(self) -> None:
        """Populate the summary with the exception info. Already called by constructor."""
        print("The student submission cannot be tested!", file=self.output_f)
        print("The autograder thinks this is an issue on the student's end, but please reach out if you don't think so, or if you have questions.", file=self.output_f)
        print(file=self.output_f)

        print(format_traceback(self.exception), end="", file=self.output_f)

    def get_summary(self) -> JsonSummary:
        return {
            "score": self.score,
            "output": self.output_f.getvalue(),
            "output_format": OUTPUT_FORMAT,
            "stdout_visibility": "visible",
            "tests": [],
        }

    def report(self, should_print_summary: bool) -> None:
        summary = self.get_summary()
        write_summary(summary)
        if should_print_summary:
            print_summary(summary)

def run_test_cases(cases: List[Case]) -> List[JsonTestCase]:
    tests = []
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
            output = format_traceback(e)

        status: JsonStatus = "passed" if passed else "failed"
        test_info: JsonTestCase = {
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


def load_submission_metadata() -> JsonMetadata:
    with open("submission_metadata.json", "r") as f:
        s = f.read()
        metadata: Dict[str, Any] = json.loads(s)

        # HACK: does not check validity. not a clear way to do this in stdlib
        return cast(JsonMetadata, metadata)

def write_summary(summary: JsonSummary) -> None:
    with open(WHERE_THE_RESULTS_GO, "w") as f:
        f.write(json.dumps(summary))

def print_summary(summary: JsonSummary) -> None:
    print(f"Assignment Score: {summary['score']}")
    print()
    print(summary["output"])

    for test in summary["tests"]:
        # TODO: we're assuming that scripts don't use level 1 or 2 headings
        print(f"## [{test['status'].upper()}] {test['name']}")
        for line in test["output"].splitlines():
            print(line)
        print()

def autograder_main(get_test_cases: Callable[[JsonMetadata], List[Case]], should_print_summary: bool) -> int:
    metadata = load_submission_metadata()
    cases: List[Case]
    try:
        cases = get_test_cases(metadata) # @raise
    except AutograderError as e:
        # the submission can't be tested! we need to report this to the student.
        summary_bad = SummaryBad(exception=e)
        summary_bad.report(should_print_summary)
        return EXIT_FAILURE

    # set max_score dynamically based on however many points the assignment is worth
    max_score: float = float(metadata["assignment"]["total_points"])

    # run the test cases!
    tests: List[JsonTestCase] = run_test_cases(cases)
    # how did they go?
    summary = SummaryGood(tests, max_score=max_score)

    # write/summarize the results!
    summary.report(should_print_summary)

    # the exit code should always be zero if we're running on
    # Gradescope, but for local tests it's helpful as an indicator of
    # failed tests.
    if not summary.all_passed() and should_print_summary:
        return EXIT_FAILURE
    else:
        return EXIT_SUCCESS

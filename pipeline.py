from cases import CaseAdHoc
from core import format_traceback
from io_trace import Read, Write
from util import *
import io_trace

from io import StringIO
from typing import List, Optional, Tuple, Any, Callable, TypeVar, Type, Set, cast

class EarlyReturn(Exception):
    pass

class CasePipeline(CaseAdHoc):
    GoldenObj = TypeVar("GoldenObj")
    TestObj = TypeVar("TestObj")

    varname: str
    in_code: bool

    def __init__(self,
                 visible: bool,
                 name: str,
                 runner: Callable[["CasePipeline"], None],
                 varname: str = "obj",
                 warning: bool = False) -> None:
        super().__init__(visible=visible, name=name, warning=warning,
                         runner=cast(Callable[["CaseAdHoc"], None], runner))
        self.varname = varname
        self.in_code = False

    def run(self) -> None:
        try:
            (self.runner)(self)
        except EarlyReturn:
            pass
        self.run_post()

    def catch(self, f: Callable[[], Any]) -> Tuple[Any, List[Read | Write]]:
        try:
            return io_trace.capture(f)
        except Exception as e:
            # case failed
            self.expect(False)

            # print exception
            self.finish_step_log(joy=False)
            self.print(format_traceback(e), end="")

            raise EarlyReturn

    def start_step_log(self) -> None:
        if self.in_code:
            return
        self.print("```text", new_line=True)
        self.in_code = True

    def finish_step_log(self, joy: bool = True) -> None:
        if not self.in_code:
            return
        self.print("```", new_line=True)
        if joy and self.passed:
            self.print("All steps completed successfully.")
        self.in_code = False

    def expect_attrs(self, obj: Any, required_attrs: Set[str],
                     obj_name: Optional[str] = None) -> None:
        def enumerate_attrs(attrs: Set[str]) -> str:
            assert len(attrs) > 0
            if len(attrs) == 1:
                [attr] = attrs
                s = f"attribute `{attr}`.\n"
            else:
                s = f"following attribute(s):\n"
                for attr in attrs:
                    s += f"- `{attr}`\n"
            return s

        if obj_name is None:
            obj_name = f"`{self.varname}`"

        extra, missing = cmp_attributes(obj, required_attrs)

        if self.expect(len(extra) == 0 and len(missing) == 0):
            return

        self.finish_step_log(joy=False)

        if len(missing) > 0:
            self.print(f"{obj_name} is unexpectedly missing the ", end="")
            self.print(enumerate_attrs(missing), end="")

        if len(extra) > 0:
            self.print(f"{obj_name} unexpectedly has the ", end="")
            self.print(enumerate_attrs(extra), end="")

        raise EarlyReturn

    def init(self, golden_t: Type[GoldenObj], test_t: Type[TestObj], args: Tuple[Any, ...],
             args_test: Optional[Tuple[Any, ...]] = None,
             cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
             fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ,
             varname: Optional[str] = None) -> Tuple[GoldenObj, TestObj]:
        if varname is None:
            varname = self.varname
        expr: str = f"{test_t.__name__}{fmt_args(args)}"
        args_golden = args
        if args_test is None:
            args_test = args
        return self.funcall(
            golden_f=lambda: golden_t(*args_golden), test_f=lambda: test_t(*args_test),
            assign_to=varname, expr_override=expr,
            cmp_ret=lambda e, a: True,
            cmp_io=cmp_io, fmt_io=fmt_io,
        )

    def method(self, golden: GoldenObj, golden_f: Callable[..., Any],
               test: TestObj, test_f: Callable[..., Any],
               args: Tuple[Any, ...] = (),
               args_test: Optional[Tuple[Any, ...]] = None,
               cmp_ret: Callable[[Any, Any], bool] = cmp_ret_equ,
               repr_ret: Callable[[Any], str] = repr,
               describe_ret: str = "Return value",
               cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
               fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ,
               varname: Optional[str] = None,
               assign_to: Optional[str] = None,
               expr_override: Optional[str] = None) -> Tuple[Any, Any]:
        if varname is None:
            varname = self.varname
        expr: str
        if expr_override is None:
            expr = f"{varname}.{test_f.__name__}{fmt_args(args)}"
        else:
            expr = expr_override
        args_golden = args
        if args_test is None:
            args_test = args
        return self.funcall(
            golden_f=golden_f, test_f=test_f,
            args=(golden, *args_golden),
            args_test=(test, *args_test),
            expr_override=expr,
            cmp_ret=cmp_ret, repr_ret=repr_ret, describe_ret=describe_ret,
            cmp_io=cmp_io, fmt_io=fmt_io,
            assign_to=assign_to,
        )

    def funcall(self,
                golden_f: Callable[..., Any], test_f: Callable[..., Any],
                args: Tuple[Any, ...] = (),
                args_test: Optional[Tuple[Any, ...]] = None,
                cmp_ret: Callable[[Any, Any], bool] = cmp_ret_equ,
                repr_ret: Callable[[Any], str] = repr,
                describe_ret: str = "Return value",
                cmp_io: Callable[[List[Read | Write], List[Read | Write]], bool] = cmp_io_equ,
                fmt_io: Callable[[List[Read | Write], List[Read | Write], bool], str] = fmt_io_equ,
                assign_to: Optional[str] = None,
                expr_override: Optional[str] = None) -> Tuple[Any, Any]:
        self.start_step_log()
        expr: str
        if expr_override is None:
            expr = f"{test_f.__name__}{fmt_args(args)}"
        else:
            expr = expr_override
        if assign_to is not None:
            expr = f"{assign_to} = {expr}"
        self.print(f">>> {expr}")
        args_golden = args
        if args_test is None:
            args_test = args
        ret_expect, io_expect = io_trace.capture(lambda: golden_f(*args_golden))
        ret, io = self.catch(lambda: test_f(*args_test))
        self.print(fmt_io_verbatim(io), end="")
        if assign_to is None and ret is not None:
            self.print(repr_ret(ret))
        if not self.expect(cmp_ret(ret_expect, ret)):
            self.finish_step_log(joy=False)
            self.print(fmt_ret_s(repr(ret_expect), repr_ret(ret), False, describe_ret), end="")
            raise EarlyReturn
        if not self.expect(cmp_io(io_expect, io)):
            self.finish_step_log(joy=False)
            self.print(fmt_io(io_expect, io, False), end="")
            raise EarlyReturn
        return ret_expect, ret

class Lambda:
    s: str

    def __init__(self, s: str) -> None:
        self.s = s

    def __call__(self, *args: Tuple[Any, ...]) -> Any:
        return eval(self.s)(*args)

    def __repr__(self) -> str:
        return self.s

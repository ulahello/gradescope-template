from io import TextIOWrapper
from typing import List, Tuple, Optional, Iterator, Iterable, Any, Callable, AnyStr, IO, TextIO, BinaryIO
import sys

# TODO: doublecheck that the wrappers are solid

class Read:
    val: str

    def __init__(self, val: str) -> None:
        self.val = val

    def __repr__(self) -> str:
        return f"Read({repr(self.val)})"

    def word(self) -> str:
        return "read"

class Write:
    val: str

    def __init__(self, val: str):
        self.val = val

    def __repr__(self) -> str:
        return f"Write({repr(self.val)})"

    def word(self) -> str:
        return "write"

class LineIter:
    ls: List[Read | Write]
    ls_iter: Iterator[Read | Write]
    cur: Optional[Read | Write]
    line: int

    def __init__(self, ls: List[Read | Write]):
        self.ls = ls
        self.ls_iter = iter(self.ls)
        self.cur = None
        self.line = 0

    def __next__(self) -> List[Read | Write]:
        ops = []
        while True:
            if self.cur is None:
                try:
                    self.cur = next(self.ls_iter)
                except StopIteration:
                    self.cur = None
                if self.cur is None:
                    break

            assert self.cur is not None

            cur = self.cur
            lines = cur.val.splitlines(True)
            if len(lines) > 1:
                self.cur.val = "".join(lines[1:])
            else:
                self.cur = None
            line = lines[0]
            ops.append(type(cur)(line))
            if line.splitlines(False) != line.splitlines(True):
                # we found the line ending!
                break

        if len(ops) == 0:
            raise StopIteration
        return ops

    def __iter__(self) -> "LineIter":
        LineIter.__init__(self, self.ls)
        return self

class Log:
    ls: List[Read | Write]

    def __init__(self, init_ls: Optional[List[Read | Write]]=None):
        if init_ls is None:
            self.ls = []
        else:
            self.ls = init_ls

    def log(self, obj: Read | Write) -> None:
        if len(self.ls) > 0:
            last = self.ls.pop()
            if type(obj) == type(last):
                # merge consecutive read/writes
                obj.val = last.val + obj.val
            else:
                self.ls.append(last)
        self.ls.append(obj)

    def swap(self) -> None:
        self.ls = []

    def __repr__(self) -> str:
        return f"Log({repr(self.ls)})"

class IOTracer(TextIO):
    inner: TextIO

    def __init__(self, io: TextIO, log: Log) -> None:
        self.inner = io

    def read(self, size: int = -1) -> str:
        ret = self.inner.read(size)
        log.log(Read(ret))
        return ret

    def readline(self, size: int = -1) -> str:
        ret = self.inner.readline(size)
        log.log(Read(ret))
        return ret

    def write(self, s: str) -> int:
        ret = self.inner.write(s)
        log.log(Write(s))
        return ret

class MockReads(TextIO):
    POP_AT: int = 0
    inner: TextIO
    queue: List[str]

    def __init__(self, io: TextIO, queue: List[str]) -> None:
        self.inner = io
        self.queue = queue

    def swap_queue(self, new: List[str]) -> List[str]:
        old = self.queue
        self.queue = new
        return old

    def pop_queue(self, size: int = -1) -> str:
        if size < 0:
            return self.queue.pop(self.POP_AT)
        else:
            s = self.queue[self.POP_AT][:size]
            self.queue[self.POP_AT] = s
            if len(self.queue[self.POP_AT]) == 0:
                self.queue.pop(self.POP_AT)
            return s

    def read(self, size: int = -1) -> str:
        try:
            return self.pop_queue(size)
        except IndexError:
            return self.inner.read(size)

    def readline(self, size: int = -1) -> str:
        try:
            s = self.queue[self.POP_AT]
            lines = s.splitlines(True)
            line = lines[0]
            new_size = min(size, len(line))
            return self.pop_queue(new_size)
        except IndexError:
            return self.inner.readline(size)

log: Log = Log()
stdin: Optional[IOTracer] = None
stdout: Optional[IOTracer] = None
stderr: Optional[IOTracer] = None

def init() -> None:
    global log, stdin, stdout, stderr
    stdin = IOTracer(MockReads(sys.stdin, []), log) # type: ignore
    stdout = IOTracer(sys.stdout, log) # type: ignore

    sys.stdin = stdin
    sys.stdout = stdout

def deinit() -> None:
    sys.stdin = sys.stdin.inner.inner # type: ignore
    sys.stdout = sys.stdout.inner # type: ignore

    global stdin, stdout, stderr
    stdin = None
    stdout = None
    stderr = None

def capture(func: Callable[[], Any], io_queue: List[str] = []) -> Tuple[Any, List[Read | Write]]:
    global log, stdin
    assert stdin is not None

    # clear console i/o log
    log.swap()
    # freshly provide queue of stdin reads
    stdin.inner.swap_queue(io_queue) # type: ignore

    ret: Any = func() # @raise

    # save i/o log
    io_log: List[Read | Write] = log.ls
    # prevent future mutation of said log by swapping it for a different object
    log.swap()

    return ret, io_log

def normalize_log(ls: Iterable[Read | Write]) -> List[Read | Write]:
    out = []
    acc = None
    for op in ls:
        if acc is None:
            acc = op
        else:
            if type(acc) == type(op):
                acc.val += op.val
            else:
                out.append(acc)
                acc = op

    if acc is not None:
        out.append(acc)
        acc = None

    return out


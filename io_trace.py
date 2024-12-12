from _generics import *

from io import TextIOWrapper, IOBase, TextIOBase, SEEK_SET
from typing import List, Tuple, Optional, Iterator, Iterable, Any, Callable, AnyStr, IO, TextIO, BinaryIO, cast
import sys

class Read:
    val: str

    def __init__(self, val: str) -> None:
        self.val = val

    def __repr__(self) -> str:
        return f"Read({repr(self.val)})"

    def __eq__(self, other: Any) -> bool:
        return other is Read and self.val == other.val

    def word(self) -> str:
        return "read"

class Write:
    val: str

    def __init__(self, val: str):
        self.val = val

    def __repr__(self) -> str:
        return f"Write({repr(self.val)})"

    def __eq__(self, other: Any) -> bool:
        return other is Write and self.val == other.val

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

class IOTracer(TextIOBase):
    inner: TextIO

    def __init__(self, io: TextIO):
        self.inner = io

    def close(self) -> None:
        return self.inner.close()

    def fileno(self) -> int:
        return self.inner.fileno()

    def flush(self) -> None:
        return self.inner.flush()

    def isatty(self) -> bool:
        return self.inner.isatty()

    def readable(self) -> bool:
        return self.inner.readable()

    def read(self, size: Optional[int] = -1) -> str:
        if size is None:
            size = -1
        global log
        ret = self.inner.read(size)
        log.log(Read(ret))
        return ret

    def readline(self, size: Optional[int] = -1) -> str: # type: ignore[override]
        if size is None:
            size = -1
        global log
        ret = self.inner.readline(size)
        log.log(Read(ret))
        return ret

    def readlines(self, hint: Optional[int] = -1) -> List[str]: # type: ignore[override]
        if hint is None:
            hint = -1
        global log
        ret = self.inner.readlines(hint)
        for read_val in ret:
            log.log(Read(read_val))
        return ret

    def seek(self, offset: int, whence: int = SEEK_SET) -> int:
        return self.inner.seek(whence)

    def seekable(self) -> bool:
        return self.inner.seekable()

    def tell(self) -> int:
        return self.inner.tell()

    def truncate(self, size: Optional[int] = None) -> int:
        return self.inner.truncate(size)

    def writable(self) -> bool:
        return self.inner.writable()

    def write(self, s: str) -> int:
        global log
        ret = self.inner.write(s)
        log.log(Write(s))
        return ret

    def writelines(self, lines: Iterable[str]) -> None: # type: ignore[override]
        global log
        self.inner.writelines(lines)
        for line in lines:
            log.log(Write(line))

    def __repr__(self) -> str:
        return f"IOTracer({repr(self.inner)})"

class MockReads(TextIOBase):
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

    def pop_queue(self, size: int = -1) -> Optional[str]:
        if len(self.queue) <= self.POP_AT:
            return None
        if size < 0:
            return self.queue.pop(self.POP_AT)
        else:
            s = self.queue[self.POP_AT][:size]
            self.queue[self.POP_AT] = self.queue[self.POP_AT][size:]
            if len(self.queue[self.POP_AT]) == 0:
                self.queue.pop(self.POP_AT)
            return s

    def close(self) -> None:
        return self.inner.close()

    def fileno(self) -> int:
        return self.inner.fileno()

    def flush(self) -> None:
        return self.inner.flush()

    def isatty(self) -> bool:
        return self.inner.isatty()

    def readable(self) -> bool:
        return self.inner.readable()

    def read(self, size: Optional[int] = -1) -> str:
        if size is None:
            size = -1
        from_queue = self.pop_queue(size)
        if from_queue is None:
            return self.inner.read(size)
        return from_queue

    def readline(self, size: int = -1) -> str: # type: ignore[override]
        if len(self.queue) <= self.POP_AT:
            return self.inner.readline(size)

        s = self.queue[self.POP_AT]
        lines = s.splitlines(True)
        line = lines[0]
        new_size = min(size, len(line))
        ret = self.pop_queue(new_size)
        assert ret is not None, "unreachable"
        return ret

    def seek(self, offset: int, whence: int = SEEK_SET) -> int:
        return self.inner.seek(whence)

    def seekable(self) -> bool:
        return self.inner.seekable()

    def tell(self) -> int:
        return self.inner.tell()

    def truncate(self, size: Optional[int] = None) -> int:
        return self.inner.truncate(size)

    def writable(self) -> bool:
        return self.inner.writable()

    def write(self, s: str) -> int:
        return self.inner.write(s)

    def writelines(self, lines: Iterable[str]) -> None: # type: ignore[override]
        return self.inner.writelines(lines)

    def __repr__(self) -> str:
        return f"MockReads({repr(self.inner)})"

log: Log = Log()
stdin: Optional[IOTracer] = None
stdout: Optional[IOTracer] = None
stderr: Optional[IOTracer] = None

def init() -> None:
    global stdin, stdout, stderr
    stdin = IOTracer(cast(TextIO, MockReads(sys.stdin, [])))
    stdout = IOTracer(sys.stdout)

    sys.stdin = stdin
    sys.stdout = stdout

def deinit() -> None:
    assert isinstance(sys.stdin, IOTracer)
    assert isinstance(sys.stdin.inner, MockReads)
    assert isinstance(sys.stdout, IOTracer)

    sys.stdin = sys.stdin.inner.inner
    sys.stdout = sys.stdout.inner

    global stdin, stdout, stderr
    stdin = None
    stdout = None
    stderr = None

def capture(func: Callable[[], T], io_queue: List[str] = []) -> Tuple[T, List[Read | Write]]:
    global log, stdin
    assert stdin is not None
    assert isinstance(stdin.inner, MockReads)

    # clear console i/o log
    log.swap()
    # freshly provide queue of stdin reads
    stdin.inner.swap_queue(io_queue)

    ret: T = func() # @raise

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


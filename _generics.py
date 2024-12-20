from typing import TypeVar

# Python 3.11 and earlier do not support the syntax for per-function
# type parameters, so we need these type variables. Extraordinarily,
# they cannot be defined multiple times across all imported files, so
# we have a central definition place to prevent circular imports.

T = TypeVar("T")

# Expected => X ("eXpected")
# Actual   => Y ("anY")
X = TypeVar("X")
Xnum = TypeVar("Xnum", bound=int | float)
Xs = TypeVar("Xs")
Y = TypeVar("Y")
Ys = TypeVar("Ys")

# pipeline
GoldenObj = TypeVar("GoldenObj")
GoldenRet = TypeVar("GoldenRet")
TestObj = TypeVar("TestObj")
TestRet = TypeVar("TestRet")

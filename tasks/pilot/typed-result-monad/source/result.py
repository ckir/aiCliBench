"""Typed Result[T, E] Monad."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class UnwrapError(Exception):
    pass


class Result(Generic[T, E]):
    def is_ok(self) -> bool:
        raise NotImplementedError

    def is_err(self) -> bool:
        raise NotImplementedError

    def unwrap(self) -> T:
        raise NotImplementedError

    def unwrap_or(self, default: T) -> T:
        raise NotImplementedError

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        raise NotImplementedError

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        raise NotImplementedError

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        raise NotImplementedError


class Ok(Result[T, Any]):
    def __init__(self, value: T) -> None:
        self.value = value


class Err(Result[Any, E]):
    def __init__(self, error: E) -> None:
        self.error = error

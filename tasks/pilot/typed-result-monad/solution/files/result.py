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

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Ok) and self.value == other.value

    def __hash__(self) -> int:
        return hash(("Ok", self.value))

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, Any]:
        return Ok(fn(self.value))

    def map_err(self, fn: Callable[[Any], F]) -> Result[T, F]:
        return self

    def and_then(self, fn: Callable[[T], Result[U, Any]]) -> Result[U, Any]:
        return fn(self.value)


class Err(Result[Any, E]):
    def __init__(self, error: E) -> None:
        self.error = error

    def __repr__(self) -> str:
        return f"Err({self.error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Err) and self.error == other.error

    def __hash__(self) -> int:
        return hash(("Err", self.error))

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        raise UnwrapError(f"Called unwrap on Err: {self.error!r}")

    def unwrap_or(self, default: T) -> T:
        return default

    def map(self, fn: Callable[[Any], U]) -> Result[U, E]:
        return self

    def map_err(self, fn: Callable[[E], F]) -> Result[Any, F]:
        return Err(fn(self.error))

    def and_then(self, fn: Callable[[Any], Result[U, E]]) -> Result[U, E]:
        return self

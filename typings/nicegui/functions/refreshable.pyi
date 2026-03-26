"""Type stubs for NiceGUI's refreshable module.

Fixes Pylance's inability to resolve .refresh() on @ui.refreshable_method decorated methods.
"""
from typing import Any, Awaitable, Callable, Generic, TypeVar, overload

from typing_extensions import Concatenate, ParamSpec, Self

_P = ParamSpec("_P")
_T = TypeVar("_T")
_S = TypeVar("_S")


class AwaitableResponse:
    """Response from refresh() that can be awaited or called directly."""
    def __call__(self) -> None: ...
    def __await__(self) -> Any: ...


class refreshable(Generic[_P, _T]):
    """Refreshable UI function decorator.

    Creates a function with a .refresh() method that re-renders its content.
    """
    func: Callable[_P, _T]
    instance: Any

    def __init__(self, func: Callable[_P, _T]) -> None: ...

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...
    @overload
    def __get__(self, instance: object, owner: type) -> Self: ...
    def __get__(self, instance: object | None, owner: type) -> Self: ...

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T: ...

    def refresh(self, *args: Any, **kwargs: Any) -> AwaitableResponse: ...

    def prune(self) -> None: ...


class refreshable_method(Generic[_S, _P, _T], refreshable[_P, _T]):
    """Refreshable UI method decorator for class methods.

    Like @ui.refreshable but properly handles the self parameter for type checkers.
    """
    def __init__(self, func: Callable[Concatenate[_S, _P], _T]) -> None: ...

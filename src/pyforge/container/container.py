from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, get_type_hints

from .exceptions import BindingResolutionError

T = TypeVar("T")

Factory = Callable[["Container"], Any]


@dataclass
class _Binding:
    factory: Factory
    shared: bool


class Container:
    """A dependency-injection container with constructor autowiring.

    A familiar service-container shape, staying a plain Python object:
    bindings map an abstract (a type or string key) to a
    factory, optionally shared (singleton) or transient (a fresh instance
    per resolution). Anything not explicitly bound is autowired by
    inspecting the target's ``__init__`` type hints.
    """

    def __init__(self) -> None:
        self._bindings: dict[Any, _Binding] = {}
        self._instances: dict[Any, Any] = {}

    def bind(self, abstract: Any, concrete: Factory | type | None = None, *, shared: bool = False) -> None:
        """Register a binding. ``concrete`` may be a class, a factory
        callable taking the container, or omitted to bind a class to itself."""
        if concrete is None:
            concrete = abstract
        factory = self._make_factory(concrete)
        self._bindings[abstract] = _Binding(factory=factory, shared=shared)
        self._instances.pop(abstract, None)

    def singleton(self, abstract: Any, concrete: Factory | type | None = None) -> None:
        self.bind(abstract, concrete, shared=True)

    def instance(self, abstract: Any, value: Any) -> None:
        """Register an already-constructed object as a shared binding."""
        self._instances[abstract] = value

    def has(self, abstract: Any) -> bool:
        return abstract in self._bindings or abstract in self._instances

    def make(self, abstract: type[T] | str, **params: Any) -> T:
        if abstract in self._instances:
            return self._instances[abstract]

        binding = self._bindings.get(abstract)
        if binding is not None:
            if binding.shared:
                instance = binding.factory(self)
                self._instances[abstract] = instance
                return instance
            return binding.factory(self)

        if isinstance(abstract, str):
            raise BindingResolutionError(f"Nothing is bound to key '{abstract}'.")

        return self._autowire(abstract, **params)

    def call(self, fn: Callable[..., Any], **params: Any) -> Any:
        """Call ``fn``, resolving any missing keyword arguments from the
        container based on its type hints."""
        kwargs = self._resolve_parameters(fn, params)
        return fn(**kwargs)

    def _make_factory(self, concrete: Factory | type) -> Factory:
        if inspect.isclass(concrete):
            return lambda c: c._autowire(concrete)
        return concrete

    def _autowire(self, target: type[T], **params: Any) -> T:
        if not inspect.isclass(target):
            raise BindingResolutionError(f"Cannot resolve non-class target: {target!r}")
        try:
            kwargs = self._resolve_parameters(target.__init__, params, skip_self=True)
        except BindingResolutionError as exc:
            raise BindingResolutionError(f"Cannot autowire {target.__name__}: {exc}") from exc
        return target(**kwargs)

    def _resolve_parameters(
        self, fn: Callable[..., Any], provided: dict[str, Any], *, skip_self: bool = False
    ) -> dict[str, Any]:
        signature = inspect.signature(fn)
        try:
            hints = get_type_hints(fn)
        except (NameError, TypeError):
            # An unresolvable forward reference in an annotation shouldn't
            # break autowiring for parameters that don't need it.
            hints = {}

        resolved: dict[str, Any] = {}
        for name, parameter in signature.parameters.items():
            if skip_self and name == "self":
                continue
            if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if name in provided:
                resolved[name] = provided[name]
                continue

            annotation = hints.get(name, parameter.annotation)
            has_default = parameter.default is not inspect.Parameter.empty

            if annotation is inspect.Parameter.empty:
                if has_default:
                    continue
                raise BindingResolutionError(
                    f"Cannot resolve parameter '{name}': no type hint and no default value."
                )

            if not inspect.isclass(annotation):
                if has_default:
                    continue
                raise BindingResolutionError(
                    f"Cannot resolve parameter '{name}': annotation {annotation!r} is not a bindable type."
                )

            if self.has(annotation):
                resolved[name] = self.make(annotation)
            elif has_default:
                continue
            else:
                resolved[name] = self._autowire(annotation)

        return resolved


container = Container()
"""The framework's default, process-wide container instance.

Using a shared default keeps everyday usage convenient (a global resolver,
no container to thread through every call) while still allowing a full
custom :class:`Container` to be constructed and passed explicitly (e.g. in
tests) where isolation matters.
"""

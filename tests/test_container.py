import pytest

from pyforge.container import BindingResolutionError, Container


class Engine:
    def start(self) -> str:
        return "vroom"


class GasEngine(Engine):
    def start(self) -> str:
        return "gas vroom"


class Car:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine


class Unresolvable:
    def __init__(self, mystery) -> None:  # no type hint, no default
        self.mystery = mystery


def test_autowires_concrete_dependencies() -> None:
    container = Container()
    car = container.make(Car)
    assert isinstance(car.engine, Engine)
    assert car.engine.start() == "vroom"


def test_bind_maps_abstract_to_concrete() -> None:
    container = Container()
    container.bind(Engine, GasEngine)
    car = container.make(Car)
    assert isinstance(car.engine, GasEngine)


def test_singleton_returns_the_same_instance() -> None:
    container = Container()
    container.singleton(Engine, GasEngine)
    assert container.make(Engine) is container.make(Engine)


def test_bind_without_singleton_is_transient() -> None:
    container = Container()
    container.bind(Engine, GasEngine)
    assert container.make(Engine) is not container.make(Engine)


def test_instance_registers_an_already_built_object() -> None:
    container = Container()
    engine = GasEngine()
    container.instance(Engine, engine)
    assert container.make(Engine) is engine


def test_make_raises_for_unresolvable_parameter() -> None:
    container = Container()
    with pytest.raises(BindingResolutionError):
        container.make(Unresolvable)


def test_make_raises_for_unbound_string_key() -> None:
    container = Container()
    with pytest.raises(BindingResolutionError):
        container.make("not-bound")


def test_call_resolves_missing_keyword_arguments() -> None:
    container = Container()

    def handler(engine: Engine, label: str) -> str:
        return f"{label}: {engine.start()}"

    assert container.call(handler, label="car") == "car: vroom"

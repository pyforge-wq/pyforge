from typing import ClassVar

import pytest

from pyforge.validation import FormRequest, validate
from pyforge.validation.rules import RULE_REGISTRY


def test_required_field_missing() -> None:
    errors = validate({}, {"name": "required"})
    assert errors == {"name": ["This field is required."]}


def test_optional_field_absent_is_fine() -> None:
    errors = validate({}, {"name": "string|max:10"})
    assert errors == {}


def test_email_rule() -> None:
    assert validate({"email": "not-an-email"}, {"email": "email"}) != {}
    assert validate({"email": "a@b.com"}, {"email": "email"}) == {}


def test_min_max_on_strings_measure_length() -> None:
    assert validate({"name": "ab"}, {"name": "min:3"}) != {}
    assert validate({"name": "abc"}, {"name": "min:3"}) == {}
    assert validate({"name": "abcdef"}, {"name": "max:3"}) != {}


def test_min_max_on_numbers_measure_value() -> None:
    assert validate({"age": 5}, {"age": "numeric|min:18"}) != {}
    assert validate({"age": 21}, {"age": "numeric|min:18"}) == {}


def test_in_rule() -> None:
    assert validate({"role": "admin"}, {"role": "in:admin,user"}) == {}
    assert validate({"role": "root"}, {"role": "in:admin,user"}) != {}


def test_confirmed_rule() -> None:
    assert validate(
        {"password": "secret123", "password_confirmation": "secret123"},
        {"password": "required|min:8|confirmed"},
    ) == {}
    assert validate(
        {"password": "secret123", "password_confirmation": "different"},
        {"password": "required|min:8|confirmed"},
    ) != {}


def test_multiple_rules_accumulate_errors() -> None:
    errors = validate({"email": "bad"}, {"email": "required|email|min:20"})
    assert set(errors["email"]) == {"Must be a valid email address.", "Must be at least 20."}


def test_unknown_rule_raises() -> None:
    with pytest.raises(ValueError):
        validate({"x": "y"}, {"x": "not-a-real-rule"})


def test_form_request_raises_http_exception_with_errors() -> None:
    class CreateUserRequest(FormRequest):
        rules: ClassVar[dict[str, str]] = {"name": "required|string", "email": "required|email"}

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        CreateUserRequest({"name": "Ada", "email": "bad"})
    assert excinfo.value.status_code == 422
    assert "email" in excinfo.value.detail["errors"]


def test_form_request_exposes_validated_data_via_attribute_access() -> None:
    class CreateUserRequest(FormRequest):
        rules: ClassVar[dict[str, str]] = {"name": "required|string", "email": "required|email"}

    request = CreateUserRequest({"name": "Ada", "email": "ada@example.com", "extra": "ignored"})
    assert request.name == "Ada"
    assert request.validated() == {"name": "Ada", "email": "ada@example.com"}
    with pytest.raises(AttributeError):
        _ = request.extra


def test_all_registered_rule_names_are_recognized_by_validate() -> None:
    # A present, truthy value so validate() actually reaches the registry
    # lookup instead of short-circuiting on an absent field.
    rules_needing_a_param = {"min": "min:1", "max": "max:10", "in": "in:1,2"}
    for name in RULE_REGISTRY:
        if name in ("confirmed", "unique"):
            continue  # handled specially in validate(), not via the registry directly
        rule_string = rules_needing_a_param.get(name, name)
        try:
            validate({"field": "1"}, {"field": rule_string})
        except ValueError as exc:
            pytest.fail(f"rule '{name}' raised: {exc}")

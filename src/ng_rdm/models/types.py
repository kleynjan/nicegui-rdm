from typing import NamedTuple, Any, Callable

# helper classes
class Validator(NamedTuple):
    """Optional element in a FieldSpec, for field validation"""
    message: str
    validator: Callable[[Any, dict], bool]  # value, item -> is_valid

class FieldSpec(NamedTuple):
    """Field configuration for store initialization"""
    validators: list[Validator]
    normalizer: Callable[[Any], Any] | None = None  # value -> normalized_value

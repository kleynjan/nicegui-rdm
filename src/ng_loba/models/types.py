from typing import NamedTuple, Any, Callable, List, Optional

# helper classes
class Validator(NamedTuple):
    """Optional element in a FieldSpec, for field validation"""
    message: str
    validator: Callable[[Any, dict], bool]  # value, item -> is_valid

class FieldSpec(NamedTuple):
    """Field configuration for store initialization"""
    validators: List[Validator]
    normalizer: Optional[Callable[[Any], Any]] = None  # value -> normalized_value

"""Pure unit tests for nutrition value parsing — no DB needed."""
import math
import pytest
from app.utils.nutrition import safe_float_conversion, convert_to_grams


@pytest.mark.parametrize("value,expected", [
    (None, None),
    ("", None),
    ("-", None),
    ("nan", None),
    ("N/A", None),
    ("traces", 0.0),
    ("Tr", 0.0),
    ("<0.1", 0.0),
    ("0", 0.0),
    ("12.5", 12.5),
    ("12,5", 12.5),  # European decimal
    ("10-20", 15.0),  # range → average
    ("<5", 2.5),     # half of upper bound
    (">50", 50.0),    # take the bound
    (3.14, 3.14),     # float passthrough
    ("garbage", None),
])
def test_safe_float_conversion(value, expected):
    assert safe_float_conversion(value) == expected


def test_safe_float_conversion_nan_float():
    assert safe_float_conversion(float("nan")) is None


@pytest.mark.parametrize("qty,unit,expected", [
    (100, "g", 100),
    (1, "kg", 1000),
    (500, "mg", 0.5),
    (5, "G", 5),       # case-insensitive
    (1, "ml", None),    # volume not supported
    (1, "cup", None),
])
def test_convert_to_grams(qty, unit, expected):
    assert convert_to_grams(qty, unit) == expected

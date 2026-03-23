"""
Tests for utility functions in ng_store.utils.helpers.
"""
from datetime import date, datetime

from ng_store.utils.helpers import (
    date_to_str,
    str_to_date,
    utc_datetime_to_str,
    str_to_utc_datetime,
    local_to_utc,
    utc_to_local,
    now_utc,
    vali_date_str,
    valid_time_string,
    equal_dicts,
    str_remove_chars,
    cast_variable,
    generate_random_string,
    deltatime_string_to_string,
    Config,
)


# --- Date/Time conversion ---

def test_date_to_str():
    assert date_to_str(date(2024, 6, 15)) == "2024-06-15"


def test_str_to_date():
    result = str_to_date("2024-06-15")
    assert result == date(2024, 6, 15)


def test_date_roundtrip():
    original = date(2024, 12, 31)
    assert str_to_date(date_to_str(original)) == original


def test_datetime_roundtrip():
    """UTC datetime -> string -> UTC datetime preserves value"""
    dt_str = "2024-10-10 / 15:02:00"
    utc_dt = str_to_utc_datetime(dt_str)
    back = utc_datetime_to_str(utc_dt)
    assert back == dt_str


def test_local_to_utc():
    """Naive local datetime converts to UTC"""
    naive = datetime(2024, 7, 1, 14, 0, 0)
    utc = local_to_utc(naive)
    assert utc.tzinfo is not None
    # In summer (CEST = UTC+2), 14:00 local = 12:00 UTC
    assert utc.hour == 12


def test_utc_to_local():
    """UTC datetime converts back to local"""
    naive = datetime(2024, 7, 1, 14, 0, 0)
    utc = local_to_utc(naive)
    local = utc_to_local(utc)
    assert local.hour == 14


def test_now_utc():
    """now_utc returns timezone-aware datetime"""
    dt = now_utc()
    assert dt.tzinfo is not None


# --- Validation helpers ---

def test_vali_date_str_valid():
    assert vali_date_str("2024-06-15") is None


def test_vali_date_str_invalid():
    result = vali_date_str("not-a-date")
    assert result is not None


def test_vali_date_str_wrong_format():
    result = vali_date_str("15-06-2024")
    assert result is not None


def test_valid_time_string_valid():
    assert valid_time_string("12:34") is True
    assert valid_time_string("00:00") is True
    assert valid_time_string("23:59") is True


def test_valid_time_string_invalid():
    assert valid_time_string("25:00") is False
    assert valid_time_string("abc") is False
    assert valid_time_string("12:60") is False


# --- Dict comparison ---

def test_equal_dicts_equal():
    assert equal_dicts({"a": 1, "b": 2}, {"a": 1, "b": 2}) is True


def test_equal_dicts_not_equal():
    assert equal_dicts({"a": 1, "b": 2}, {"a": 1, "b": 3}) is False


def test_equal_dicts_ignore_keys():
    assert equal_dicts(
        {"a": 1, "b": 2, "id": 100},
        {"a": 1, "b": 2, "id": 200},
        ignore_keys=["id"]
    ) is True


# --- String utilities ---

def test_str_remove_chars():
    assert str_remove_chars("hello!", "e!") == "hllo"


def test_generate_random_string_length():
    s = generate_random_string(20)
    assert len(s) == 20


def test_generate_random_string_default():
    s = generate_random_string()
    assert len(s) == 13


def test_generate_random_string_unique():
    """Two random strings should (almost certainly) differ"""
    a = generate_random_string(20)
    b = generate_random_string(20)
    assert a != b


# --- Type casting ---

def test_cast_variable_int():
    assert cast_variable("42", "int") == 42


def test_cast_variable_float():
    assert cast_variable("3.14", "float") == 3.14


def test_cast_variable_int_with_decimal():
    """Int casting with decimal goes through float first"""
    assert cast_variable("3.9", "int") == 3


def test_cast_variable_bool_false():
    assert cast_variable("False", "bool") is False


def test_cast_variable_bool_true():
    assert cast_variable("1", "bool") is True


def test_cast_variable_unknown_type():
    import pytest
    with pytest.raises(ValueError, match="Unknown type"):
        cast_variable("x", "complex_number")


# --- Deltatime ---

def test_deltatime_string_to_string():
    result = deltatime_string_to_string(
        "2024-12-12 / 14:34:15",
        "2024-12-12 / 14:36:43"
    )
    assert "2 mins" in result
    assert "28 secs" in result


def test_deltatime_hours():
    result = deltatime_string_to_string(
        "2024-12-12 / 10:00:00",
        "2024-12-12 / 12:30:45"
    )
    assert "2 hours" in result
    assert "30 mins" in result


# --- Config ---

def test_config_dot_access():
    c = Config({"name": "test", "port": 8080})
    assert c.name == "test"
    assert c.port == 8080


def test_config_nested():
    c = Config({"db": {"host": "localhost", "port": 5432}})
    assert c.db.host == "localhost"
    assert c.db.port == 5432


def test_config_missing_returns_none():
    c = Config({"name": "test"})
    assert c.nonexistent is None


def test_config_list_of_dicts():
    c = Config({"entries": [{"a": 1}, {"a": 2}]})
    assert c.entries[0].a == 1
    assert c.entries[1].a == 2


import string
import secrets
from datetime import date, datetime
import pytz

from ng_rdm.components.i18n import _

TIMEZONE_STRING = 'Europe/Amsterdam'
TIMEZONE_PYTZ = pytz.timezone(TIMEZONE_STRING)


def configure_timezone(tz_string: str) -> None:
    """Set the timezone used by all date/time helpers."""
    global TIMEZONE_STRING, TIMEZONE_PYTZ
    TIMEZONE_STRING = tz_string
    TIMEZONE_PYTZ = pytz.timezone(tz_string)

# naive_dt = datetime(2024,10,10,15,2) # "our time"
# > 2024-10-10 15:02:00
#
# *naive -> utc*
# utc_dt = local_to_utc(naive_dt)
# > 2024-10-10 13:02:00+00:00
#
# *utc -> naive*
# naive_dt2 = utc_to_local(utc_dt)
# > 2024-10-10 15:02:00
#
# *utc -> naive -> str*    # this is the repr from the stores after hydration
# utc_str = utc_datetime_to_str(utc_dt)
# > 2024-10-10 / 15:02:00
#
# *str -> utc*      # this is dehydration -> db
# utc_dt2 = str_to_utc_datetime(utc_str)
# > 2024-10-10 13:02:00+00:00


def local_to_mysql_utc(dt: datetime) -> str:
    """Convert a naive datetime to UTC."""
    """Eg, "2024-12-18 14:05:41.000" instead of "2024-12-18 14:05:41.000+00:00"."""
    return local_to_utc(dt).strftime('%Y-%m-%d %H:%M:%S.%f')

def local_to_utc(dt: datetime) -> datetime:
    """Convert a naive datetime to UTC."""
    local_dt = TIMEZONE_PYTZ.localize(dt)
    return local_dt.astimezone(pytz.utc)

def utc_to_local(dt: datetime) -> datetime:
    """Convert the UTC datetime to the local timezone."""
    return dt.astimezone(TIMEZONE_PYTZ)

def utc_datetime_to_str(dt: datetime) -> str:
    """Hydration: format the datetime as a string."""
    return utc_to_local(dt).strftime('%Y-%m-%d / %H:%M:%S')

def str_to_utc_datetime(dt_str: str) -> datetime:
    """Dehydration: parse the datetime string to a UTC datetime object."""
    naive = datetime.strptime(dt_str, '%Y-%m-%d / %H:%M:%S')
    return local_to_utc(naive)

# small helpers

def now_utc() -> datetime:
    """A non-naive now() replacement to allow datetime comparisons."""
    return local_to_utc(datetime.now())

def date_to_str(dd: date) -> str:
    """Format the date as a string."""
    return dd.strftime('%Y-%m-%d')

def str_to_date(dd_str: str) -> date:
    """Parse the date string to a date object."""
    return datetime.strptime(dd_str, '%Y-%m-%d').date()

def str_to_datetime(dt_str: str) -> datetime:
    """Parse the datetime string to a naive datetime object."""
    return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S.%f')

def vali_date_str(date_str: str) -> None | str:
    """Validate the date string: return None if OK, error message otherwise."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return None
    except ValueError:
        return _("enter a valid date")


def equal_dicts(d1, d2, ignore_keys=[]):
    d1_filtered = {k: v for k, v in d1.items() if k not in ignore_keys}
    d2_filtered = {k: v for k, v in d2.items() if k not in ignore_keys}
    return d1_filtered == d2_filtered


def str_remove_chars(original_str, chars):
    """Remove chars from original_str. Ex usage: rm_char("hello!", "e!") -> "hllo" """
    return original_str.translate(str.maketrans('', '', chars))


# Dictionary mapping type names to actual Python types
type_map = {
    "bool": bool,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    # Add other types as needed
}

def cast_variable(value, type_name):
    target_type = type_map.get(type_name)

    # handle int casting with decimals -> float -> int
    if type_name == "int" and "." in value:
        value = float(value)
        # value.split(".")[0]

    if type_name == "bool" and value == "False":
        value = False

    if target_type is None:
        raise ValueError(f"Unknown type name: {type_name}")

    # Cast the value to the target type
    return target_type(value)


def generate_random_string(length=13):
    """Generate a random string of uppercase letters and digits (of given length)."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def valid_time_string(value: str) -> bool:
    "Given a '12:34' string, return True if it's a valid time, False otherwise."
    try:
        datetime.strptime(value, '%H:%M')
        return True
    except ValueError:
        return False


def deltatime_string_to_string(t1, t2):
    # # Example usage
    # t1 = "2024-12-12 / 14:34:15"
    # t2 = "2024-12-12 / 14:36:43"
    # print(deltatime_string_to_string(t1, t2))  # Output: "2 mins, 28 secs"

    # Define the format of the input timestamps
    time_format = "%Y-%m-%d / %H:%M:%S"

    # Parse the timestamps
    start_time = datetime.strptime(t1, time_format)
    end_time = datetime.strptime(t2, time_format)

    # Calculate the difference
    delta = end_time - start_time

    # Extract hours, minutes, and seconds from the difference
    hours, remainder = divmod(delta.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the result
    result = []
    if hours > 0:
        result.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        result.append(f"{int(minutes)} min{'s' if minutes > 1 else ''}")
    if seconds > 0:
        result.append(f"{int(seconds)} sec{'s' if seconds > 1 else ''}")

    return ", ".join(result)


class Config(dict):
    # make config dot.accessible, returns None if key not found
    # (note: None can be passed to chain() instead of a list)
    # init converts source dict & nested dicts to Config objects
    def __init__(self, src_dict: dict):
        super().__init__(src_dict)
        for k, v in src_dict.items():
            if isinstance(v, dict):
                self[k] = Config(v)
            elif isinstance(v, list) and isinstance(v[0], dict):
                self[k] = [Config(i) for i in v]
            else:
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        super().__setitem__(key, value)
        self.__dict__.update({key: value})

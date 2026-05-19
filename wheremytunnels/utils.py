"""Common utility functions"""


def is_psutil_conn(obj) -> bool:
    return hasattr(obj, "status") and hasattr(obj, "laddr") and hasattr(obj, "raddr")


def conn_validator(_, __, value):
    if not is_psutil_conn(value):
        raise TypeError(f"Expected psutil connection-like object, got {type(value)!r}")

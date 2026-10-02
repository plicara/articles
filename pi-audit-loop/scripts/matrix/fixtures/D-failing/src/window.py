"""Sliding-window helpers."""


def last_n(items, n):
    """Return the last ``n`` items of ``items`` as a list."""
    if n < 0:
        raise ValueError("n must be non-negative")
    return list(items[-n:])

"""Small descriptive statistics helpers."""


def mean(values):
    """Arithmetic mean, or 0.0 for an empty sequence."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def median(values):
    """Median, or 0.0 for an empty sequence."""
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def spread(values):
    """Difference between the largest and smallest value, or 0.0 if empty."""
    if not values:
        return 0.0
    return max(values) - min(values)

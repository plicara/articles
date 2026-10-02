"""Aggregate ``(date, amount)`` records into per-period summaries."""

from itertools import groupby


def summarize_daily(records):
    """Group records by calendar day. ``records`` must be sorted by date."""
    result = []
    for key, group in groupby(records, key=lambda r: r[0]):
        amounts = [amount for _, amount in group]
        result.append(
            {"period": key, "total": round(sum(amounts), 2), "count": len(amounts)}
        )
    return result


def summarize_monthly(records):
    """Group records by calendar month. ``records`` must be sorted by date."""
    result = []
    for key, group in groupby(records, key=lambda r: (r[0].year, r[0].month)):
        amounts = [amount for _, amount in group]
        result.append(
            {"period": key, "total": round(sum(amounts), 2), "count": len(amounts)}
        )
    return result


def summarize_quarterly(records):
    """Group records by calendar quarter. ``records`` must be sorted by date."""
    result = []
    for key, group in groupby(
        records, key=lambda r: (r[0].year, (r[0].month - 1) // 3 + 1)
    ):
        amounts = [amount for _, amount in group]
        result.append(
            {"period": key, "total": round(sum(amounts), 2), "count": len(amounts)}
        )
    return result

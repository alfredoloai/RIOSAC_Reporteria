from __future__ import annotations

from datetime import date, timedelta
from typing import Iterator


def iter_dates(start: date, end: date) -> Iterator[date]:
	"""Yield dates from start to end inclusive."""
	if end < start:
		raise ValueError("start date must be on or before end date")

	current = start
	while current <= end:
		yield current
		current += timedelta(days=1)

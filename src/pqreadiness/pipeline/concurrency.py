"""Run a function over many items with a bounded thread pool.

Probing is I/O-bound (waiting on the network), so threads are a good fit and
keep the code simple. Results stream back as each item finishes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

In = TypeVar("In")
Out = TypeVar("Out")


def map_concurrent(
    func: Callable[[In], Out],
    items: Iterable[In],
    max_workers: int,
) -> Iterator[Out]:
    """Apply `func` to each item across `max_workers` threads, yielding results
    as they complete (order is not preserved)."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(func, item) for item in items]
        for future in as_completed(futures):
            yield future.result()

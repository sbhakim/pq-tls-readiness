"""Statistics used in the paper.

- Wilson score interval: a robust confidence interval for a proportion, good
  even when the count is small or the rate is near 0 or 1 (both likely here).
- McNemar's test: compares two paired classifiers (single-probe vs dual-probe)
  on the same targets, i.e. how much extra hybrid support dual-probing finds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# 1.96 = z for a 95% two-sided interval.
_Z_95 = 1.959963984540054


@dataclass
class Proportion:
    """A rate with a confidence interval."""

    successes: int
    total: int
    rate: float
    low: float
    high: float


def wilson_interval(successes: int, total: int, z: float = _Z_95) -> Proportion:
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return Proportion(0, 0, 0.0, 0.0, 0.0)

    phat = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    center = (phat + z2 / (2 * total)) / denom
    margin = (z * math.sqrt((phat * (1 - phat) + z2 / (4 * total)) / total)) / denom
    return Proportion(
        successes=successes,
        total=total,
        rate=phat,
        low=max(0.0, center - margin),
        high=min(1.0, center + margin),
    )


@dataclass
class McNemarResult:
    """Outcome of a McNemar test on two paired binary classifiers."""

    b: int          # only classifier A positive
    c: int          # only classifier B positive
    statistic: float
    p_exact: float  # two-sided exact binomial p-value on the discordant pairs
    note: str


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact binomial p-value for McNemar's test.

    Under H0 the discordant pairs split 50/50 between b and c, so the p-value
    is the two-sided binomial tail probability of a split at least as extreme
    as the observed one. Exact for any n, and the reportable number when the
    discordant count is small.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def mcnemar(b: int, c: int) -> McNemarResult:
    """McNemar's test from the two discordant counts.

    `b` = targets where only A found the property, `c` = only B. The exact
    binomial p-value is always computed; the continuity-corrected chi-square
    statistic is added when the discordant count is large enough for the
    asymptotic approximation to hold.
    """
    n = b + c
    p_exact = mcnemar_exact_p(b, c)
    if n == 0:
        return McNemarResult(b, c, 0.0, p_exact, "no discordant pairs")
    if n < 25:
        return McNemarResult(b, c, float("nan"), p_exact, "exact binomial (small n)")

    statistic = (abs(b - c) - 1) ** 2 / n
    return McNemarResult(
        b, c, statistic, p_exact, "chi-square with continuity correction, df=1"
    )

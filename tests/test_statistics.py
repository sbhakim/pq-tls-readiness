"""Wilson interval and McNemar behave sensibly at the edges."""

from __future__ import annotations

import math

import pytest

from pqreadiness.analysis.statistics import mcnemar, wilson_interval


def test_wilson_zero_total():
    p = wilson_interval(0, 0)
    assert p.rate == 0.0 and p.low == 0.0 and p.high == 0.0


def test_wilson_all_success_bounds():
    p = wilson_interval(10, 10)
    assert p.rate == 1.0
    # Upper bound sits at 1.0 (approx, since it's a float); lower bound is
    # below 1.0 because 10/10 is not proof the true rate is 100%.
    assert p.high == pytest.approx(1.0)
    assert p.low < 1.0


def test_wilson_half():
    p = wilson_interval(50, 100)
    assert abs(p.rate - 0.5) < 1e-9
    assert p.low < 0.5 < p.high


def test_mcnemar_no_discordant():
    result = mcnemar(0, 0)
    assert result.statistic == 0.0


def test_mcnemar_small_n_flagged():
    result = mcnemar(3, 2)
    assert math.isnan(result.statistic)
    assert "exact" in result.note


def test_mcnemar_large_discordant():
    # Strong asymmetry (70 vs 0) should give a large statistic.
    result = mcnemar(70, 0)
    assert result.statistic > 50


def test_mcnemar_exact_p_matches_paper_case():
    # 19 discordant pairs all favoring the dual-probe (the pilot result):
    # p = 2 * (1/2)^19 ~= 3.8e-6, i.e. the paper's p < 1e-5.
    result = mcnemar(19, 0)
    assert result.p_exact < 1e-5


def test_mcnemar_exact_p_balanced_is_one():
    result = mcnemar(5, 5)
    assert result.p_exact == pytest.approx(1.0)


def test_mcnemar_exact_p_no_discordant():
    assert mcnemar(0, 0).p_exact == 1.0

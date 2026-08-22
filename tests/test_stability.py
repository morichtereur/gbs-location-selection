"""The Monte Carlo. Checks the sampling is actually sampling, and that the
verdict thresholds mean what the README says they mean."""

from __future__ import annotations

import numpy as np
import pytest

from src import config as C
from src.stability import Z90, _wgi_sigma, run
from tests.test_score import make, panel  # noqa: F401


def test_wgi_sigma_inverts_the_published_interval():
    # A 90% interval of +/- 10 points implies this sigma by construction.
    sigma = _wgi_sigma(40.0, 60.0)
    assert sigma == pytest.approx(10.0 / Z90)
    # A publisher reporting no interval must not produce a negative sigma.
    assert _wgi_sigma(50.0, 50.0) == 0.0


def test_declared_weights_are_the_centre_of_the_draws(panel):  # noqa: F811
    rng = np.random.default_rng(C.SEED)
    declared = C.ARCHETYPES["transactional_hub"]["weights"]
    from src.score import PILLARS

    alpha = np.array([C.WEIGHT_CONCENTRATION * declared[p] for p in PILLARS])
    draws = rng.dirichlet(alpha, size=20_000)
    assert draws.sum(axis=1) == pytest.approx(np.ones(20_000))
    for i, p in enumerate(PILLARS):
        assert draws[:, i].mean() == pytest.approx(declared[p], abs=0.01)


def test_frequencies_are_probabilities_and_ranks_are_within_the_panel(panel):  # noqa: F811
    st = run(panel, "transactional_hub", draws=300)
    assert set(st.frequency) == set(panel)
    for k in panel:
        assert 0.0 <= st.frequency[k] <= 1.0
        lo, hi = st.rank_range[k]
        assert 1 <= lo <= hi <= len(panel)
        assert lo <= st.mean_rank[k] <= hi


def test_a_panel_smaller_than_top_n_puts_everyone_in_the_shortlist(panel):  # noqa: F811
    st = run(panel, "transactional_hub", draws=200)
    assert len(panel) == C.TOP_N
    for k in panel:
        assert st.frequency[k] == 1.0
        assert st.verdict(k) == "robust"


def test_same_seed_reproduces_the_run(panel):  # noqa: F811
    a = run(panel, "judgment_centre", draws=250, seed=7)
    b = run(panel, "judgment_centre", draws=250, seed=7)
    assert a.frequency == b.frequency
    c = run(panel, "judgment_centre", draws=250, seed=8)
    assert a.baseline_rank == c.baseline_rank  # baseline ignores the draws


def test_input_resampling_actually_perturbs_the_inputs(panel):  # noqa: F811
    """Guards the finding that input uncertainty barely moves the ranking.

    That claim is only meaningful if the resampling is switched on and doing
    something — a silent no-op would produce the same reassuring answer.
    """
    wide = {k: v for k, v in panel.items()}
    for m in wide.values():
        # A deliberately enormous published interval must change the outcome.
        m.wgi = {d: (m.risk_score, 0.0, 100.0) for d in C.WGI_DIMENSIONS}
    off = run(wide, "judgment_centre", draws=400, resample_inputs=False)
    on = run(wide, "judgment_centre", draws=400, resample_inputs=True,
             wgi_correlation="perfect")
    assert off.mean_rank != on.mean_rank


def test_verdict_thresholds(panel):  # noqa: F811
    st = run(panel, "transactional_hub", draws=100)
    st.frequency = {"a": 0.95, "b": 0.5, "c": 0.02}
    assert st.verdict("a") == "robust"
    assert st.verdict("b") == "contingent"
    assert st.verdict("c") == "never"


def test_thin_evidence_cannot_be_robust(panel):  # noqa: F811
    """Mumbai cleared 90% of weightings on six postings and was labelled robust.
    The frequency was right and the label was wrong."""
    st = run(panel, "transactional_hub", draws=100)
    st.frequency = {"thin": 0.99, "solid": 0.99}
    st.evidence = {"thin": C.EVIDENCE_FLOOR - 1, "solid": C.EVIDENCE_FLOOR}
    assert st.verdict("thin") == "contingent"
    assert st.verdict("solid") == "robust"
    # A candidate with no evidence entry — a country row — is unaffected.
    assert st.verdict("absent") == "never"


def test_precision_correction_recovers_a_known_share():
    """The correction inverts the mixture it claims to invert."""
    from src.stability import _correct_for_precision

    class M:
        contaminant_transactional = 0.40

    # Construct an observed share from a known truth, then recover it.
    precision, true = 0.55, 0.80
    observed = precision * true + (1 - precision) * M.contaminant_transactional
    recovered = _correct_for_precision(observed, precision, M(), "transactional_share")
    assert recovered == pytest.approx(true)


def test_precision_correction_uses_the_mirror_contaminant_for_judgment():
    from src.stability import _correct_for_precision

    class M:
        contaminant_transactional = 0.70

    precision, true = 0.55, 0.60
    # For judgment the contaminant is the mirror of the transactional mix.
    observed = precision * true + (1 - precision) * (1 - M.contaminant_transactional)
    recovered = _correct_for_precision(observed, precision, M(), "judgment_share")
    assert recovered == pytest.approx(true)


def test_precision_correction_stays_in_range_and_is_inert_when_disabled():
    from src.stability import _correct_for_precision

    class M:
        contaminant_transactional = 0.40

    for observed in (0.0, 0.5, 1.0):
        got = _correct_for_precision(observed, 0.3, M(), "transactional_share")
        assert 0.0 <= got <= 1.0
    # A perfect classifier changes nothing.
    assert _correct_for_precision(0.73, 1.0, M(), "transactional_share") == pytest.approx(0.73)
    # Neither does an absurdly low drawn precision, which would otherwise
    # divide by almost zero.
    assert _correct_for_precision(0.73, 0.01, M(), "transactional_share") == 0.73

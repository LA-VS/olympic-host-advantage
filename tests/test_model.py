import numpy as np
import pandas as pd
import pytest

from olympic_hosts.model import fit, model_sample, overdispersion_test, prepare


def synthetic_panel(true_irr=1.6, n_nations=40, n_games=12, overdispersed=False, seed=0):
    """Nations with their own baseline strength, Games of growing size, and a few hosts."""
    rng = np.random.default_rng(seed)
    rows = []
    strength = rng.lognormal(0, 1, n_nations)
    for g in range(n_games):
        host = g % n_nations
        size = 1 + g / n_games
        for n in range(n_nations):
            mu = 3 * strength[n] * size * (true_irr if n == host else 1)
            if overdispersed:
                mu = mu * rng.gamma(2.0, 0.5)
            rows.append(
                {
                    "nation_id": f"N{n:02d}",
                    "nation_name": f"Nation {n}",
                    "games_id": f"G{g:02d}",
                    "season": "Summer",
                    "medals": rng.poisson(mu),
                    "host": int(n == host),
                    "next_host": int(n == (g + 1) % n_nations),
                    "gdp_usd": np.exp(rng.normal(25, 1)),
                    "population": np.exp(rng.normal(16, 1)),
                }
            )
    df = pd.DataFrame(rows)
    df["medal_share"] = df["medals"] / df.groupby("games_id")["medals"].transform("sum")
    return prepare(df)


def test_poisson_recovers_known_host_effect():
    df = synthetic_panel(true_irr=1.6, n_nations=30, n_games=30)
    result = fit(df, "host + next_host").irr()
    assert result["ci_low"] < 1.6 < result["ci_high"]
    assert result["irr"] == pytest.approx(1.6, rel=0.15)


def test_negative_binomial_recovers_known_host_effect():
    df = synthetic_panel(true_irr=1.6, n_nations=30, n_games=30, overdispersed=True)
    result = fit(df, "host + next_host", alpha=0.5).irr()
    assert result["ci_low"] < 1.6 < result["ci_high"]


def test_overdispersion_test_flags_gamma_mixed_counts_only():
    calm = overdispersion_test(fit(synthetic_panel(seed=1), "host"))
    noisy = overdispersion_test(fit(synthetic_panel(seed=1, overdispersed=True), "host"))
    assert calm["p_value"] > 0.01
    assert noisy["p_value"] < 0.001 and noisy["alpha"] > 0.1


def test_model_sample_drops_nations_that_never_win():
    df = synthetic_panel()
    df.loc[df["nation_id"] == "N03", "medals"] = 0
    assert "N03" not in set(model_sample(df, "host")["nation_id"])


def test_model_sample_drops_rows_missing_economics_only_when_used():
    df = synthetic_panel()
    df.loc[df.index[:5], "log_gdp"] = np.nan
    assert len(model_sample(df, "host")) == len(df)
    assert len(model_sample(df, "host + log_gdp")) == len(df) - 5

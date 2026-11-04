"""Count models for the host effect.

Every model has nation fixed effects (one per nation and season, because a nation's Summer and
Winter strength differ) so the host effect is measured against each nation's own normal level.
Games fixed effects absorb the number of medals on offer at each Games, which grows over time,
and they also absorb the season indicator. Standard errors are clustered by nation.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

BOYCOTT_GAMES = ("1976S", "1980S", "1984S")
FIXED_EFFECTS = "C(nation_season) + C(games_id)"
HEADLINE_RHS = "host + next_host + log_gdp + log_pop"


def prepare(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["winter"] = (df["season"] == "Winter").astype(int)
    df["host_winter"] = df["host"] * df["winter"]
    df["nation_season"] = df["nation_id"] + "_" + df["season"]
    df["log_gdp"] = np.log(df["gdp_usd"])
    df["log_pop"] = np.log(df["population"])
    return df


def model_sample(df: pd.DataFrame, rhs: str, outcome: str = "medals") -> pd.DataFrame:
    """Rows with every covariate present, for nations with at least one medal in the sample.

    A nation with only zeros has a fixed effect of minus infinity and adds no information.
    """
    needed = [c for c in ("log_gdp", "log_pop") if c in rhs]
    data = df.dropna(subset=needed)
    return data[data.groupby("nation_season")[outcome].transform("sum") > 0]


@dataclass
class Fit:
    name: str
    result: object
    n_obs: int
    n_hosts: int

    def irr(self, term: str = "host") -> pd.Series:
        """Incidence rate ratio with a 95% confidence interval for one term."""
        b = self.result.params[term]
        lo, hi = self.result.conf_int().loc[term]
        return pd.Series(
            {"irr": np.exp(b), "ci_low": np.exp(lo), "ci_high": np.exp(hi), "p_value": self.result.pvalues[term]}
        )

    def combined_irr(self, terms: list[str]) -> pd.Series:
        """IRR for the sum of several coefficients, such as host plus host_winter."""
        weights = np.array([1.0 if n in terms else 0.0 for n in self.result.params.index])
        test = self.result.t_test(weights)
        b = float(np.squeeze(test.effect))
        lo, hi = np.squeeze(test.conf_int())
        return pd.Series(
            {"irr": np.exp(b), "ci_low": np.exp(lo), "ci_high": np.exp(hi), "p_value": float(np.squeeze(test.pvalue))}
        )


def fit(
    df: pd.DataFrame, rhs: str = HEADLINE_RHS, alpha: float | None = None, outcome: str = "medals", name: str = ""
) -> Fit:
    """Fixed effects count model with nation clustered errors.

    alpha=None fits Poisson pseudo maximum likelihood, which is consistent for the mean even under
    overdispersion and also works for a share outcome. A value fits negative binomial (NB2).
    """
    data = model_sample(df, rhs, outcome)
    family = sm.families.Poisson() if alpha is None else sm.families.NegativeBinomial(alpha=alpha)
    groups = pd.factorize(data["nation_id"])[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = smf.glm(f"{outcome} ~ {rhs} + {FIXED_EFFECTS}", data=data, family=family).fit(
            cov_type="cluster", cov_kwds={"groups": groups}, maxiter=200
        )
    return Fit(name or rhs, result, len(data), int(data["host"].sum()))


def overdispersion_test(poisson: Fit) -> dict[str, float]:
    """Cameron and Trivedi (1990) auxiliary regression test of Poisson equidispersion.

    Regress ((y - mu)^2 - y) / mu on mu with no constant. A significantly positive slope means
    variance grows faster than the mean (NB2 overdispersion), and the slope estimates alpha.
    """
    y = poisson.result.model.endog
    mu = poisson.result.fittedvalues
    aux = sm.OLS(((y - mu) ** 2 - y) / mu, mu).fit()
    return {
        "alpha": float(aux.params.iloc[0]),
        "t": float(aux.tvalues.iloc[0]),
        "p_value": float(aux.pvalues.iloc[0]),
        "pearson_dispersion": float(poisson.result.pearson_chi2 / poisson.result.df_resid),
    }


def estimate_alpha(df: pd.DataFrame, rhs: str = HEADLINE_RHS, grid: np.ndarray | None = None) -> float:
    """Maximum likelihood NB2 dispersion, found by profiling the log likelihood over a grid."""
    data = model_sample(df, rhs)
    grid = np.geomspace(0.005, 1.0, 25) if grid is None else grid
    formula = f"medals ~ {rhs} + {FIXED_EFFECTS}"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        llf = [
            smf.glm(formula, data=data, family=sm.families.NegativeBinomial(alpha=a)).fit(maxiter=200).llf for a in grid
        ]
    return float(grid[int(np.argmax(llf))])


def robustness(df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """The headline host IRR under each alternative specification."""
    specs = [
        ("Headline: negative binomial", df, HEADLINE_RHS, alpha, "medals"),
        ("Poisson instead of negative binomial", df, HEADLINE_RHS, None, "medals"),
        ("No GDP or population (all 35 hosts)", df, "host + next_host", alpha, "medals"),
        ("Boycott Games 1976 to 1984 dropped", df[~df["games_id"].isin(BOYCOTT_GAMES)], HEADLINE_RHS, alpha, "medals"),
        ("Medal share instead of count", df, HEADLINE_RHS, None, "medal_share"),
        ("Summer Games only", df[df["season"] == "Summer"], HEADLINE_RHS, alpha, "medals"),
        ("Winter Games only", df[df["season"] == "Winter"], HEADLINE_RHS, alpha, "medals"),
    ]
    rows = []
    for name, data, rhs, a, outcome in specs:
        f = fit(data, rhs, a, outcome, name)
        rows.append({"specification": name, "n_obs": f.n_obs, "hosts": f.n_hosts, **f.irr()})
    return pd.DataFrame(rows).set_index("specification")


def leave_one_host_out(df: pd.DataFrame, alpha: float, rhs: str = HEADLINE_RHS) -> pd.DataFrame:
    """Refit dropping one host Games row at a time (the nation's other Games stay in)."""
    hosts = model_sample(df, rhs)
    rows = []
    for idx in hosts.index[hosts["host"] == 1]:
        f = fit(df.drop(index=idx), rhs, alpha)
        rows.append({"dropped": df.at[idx, "games_id"], "nation": df.at[idx, "nation_name"], **f.irr()})
    return pd.DataFrame(rows)

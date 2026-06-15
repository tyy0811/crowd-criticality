from __future__ import annotations
from dataclasses import dataclass
import warnings
import numpy as np
import powerlaw


@dataclass
class PowerLawFit:
    exponent: float
    xmin: float
    p_boot: float
    lrt: dict  # name -> (R, p); R>0 favours power_law, R<0 favours the alternative

    @property
    def passes(self) -> bool:
        if self.p_boot < 0.10:
            return False
        return not any(R < 0 and p < 0.05 for (R, p) in self.lrt.values())


def _fit(x, xmin=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return powerlaw.Fit(np.asarray(x), discrete=True, xmin=xmin, verbose=False)


def fit_powerlaw(x, rng=None, n_boot=200, compute_p=True):
    f = _fit(x)
    lrt = {}
    for alt in ("lognormal", "exponential", "truncated_power_law"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            R, p = f.distribution_compare("power_law", alt, normalized_ratio=True)
        lrt[alt] = (float(R), float(p))
    p_boot = _goodness_of_fit(x, f, n_boot, rng) if compute_p else float("nan")
    return PowerLawFit(exponent=float(f.power_law.alpha),
                       xmin=float(f.power_law.xmin), p_boot=p_boot, lrt=lrt)


def _goodness_of_fit(x, f, n_boot, rng):
    """Clauset semi-parametric bootstrap p-value: synth = fitted tail above xmin
    (prob p_tail) + resampled body below; fraction of synth KS >= observed KS."""
    if rng is None:
        rng = np.random.default_rng()
    x = np.asarray(x)
    xmin, D_obs, ntot = f.power_law.xmin, f.power_law.D, x.size
    below = x[x < xmin]
    p_tail = float((x >= xmin).sum()) / ntot
    count = 0
    for _ in range(n_boot):
        n_tail = int(rng.binomial(ntot, p_tail))
        tail = np.asarray(f.power_law.generate_random(n_tail)) if n_tail else np.empty(0)
        n_below = ntot - n_tail
        body = (rng.choice(below, size=n_below, replace=True)
                if (n_below and below.size) else np.empty(0))
        synth = np.concatenate([tail, body])
        if _fit(synth).power_law.D >= D_obs:
            count += 1
    return count / n_boot

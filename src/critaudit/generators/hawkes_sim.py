from __future__ import annotations
import numpy as np
from critaudit.types import EventStream


def choose_backend(n, backend="auto"):
    if backend != "auto":
        return backend
    return "cluster" if n >= 0.9 else "thinning"


def simulate(n, horizon, mu=0.6, beta=1.0, backend="auto", rng=None):
    """Univariate exponential-kernel Hawkes, branching ratio n = alpha/beta."""
    if rng is None:
        raise ValueError("pass an explicit numpy Generator as rng")
    chosen = choose_backend(n, backend)
    if chosen == "thinning":
        times = _simulate_thinning(n, beta, mu, horizon, rng)
    elif chosen == "cluster":
        times = _simulate_cluster(n, beta, mu, horizon, rng)
    else:
        raise ValueError(f"unknown backend {chosen!r}")
    es = EventStream(times=times, horizon=float(horizon))
    _sanity(n, mu, chosen, es)
    return es


_SANITY_DONE = False


def _sanity(n, mu, backend, es):
    global _SANITY_DONE
    if _SANITY_DONE or es.times.size == 0:
        return
    _SANITY_DONE = True
    print(f"=== hawkes simulate sanity (n={n}, backend={backend}) ===")
    print(f"  N={es.times.size} rate={es.times.size / es.horizon:.4f} "
          f"expected={mu / (1 - n):.4f}")


def _simulate_thinning(n, beta, mu, horizon, rng):
    """Ogata thinning. O(1) per step: track post-jump excitation, decay on the fly."""
    alpha = n * beta
    t = 0.0
    t_last = 0.0
    exc_last = 0.0  # excitation just after the last accepted event
    ev = []
    while t < horizon:
        exc_t = exc_last * np.exp(-beta * (t - t_last))
        lam_bar = mu + exc_t  # intensity decays between events -> upper bound
        t = t + rng.exponential(1.0 / lam_bar)
        if t >= horizon:
            break
        exc_t = exc_last * np.exp(-beta * (t - t_last))
        lam = mu + exc_t
        if rng.random() * lam_bar <= lam:
            ev.append(t)
            exc_last = exc_t + alpha
            t_last = t
    return np.asarray(ev, dtype=float)


def _simulate_cluster(n, beta, mu, horizon, rng):
    """Immigrant-cluster (Hawkes-Oakes) representation: exact for exponential
    kernels, graceful where thinning's acceptance rate collapses near n->1."""
    n_imm = int(rng.poisson(mu * horizon))
    times = list(rng.uniform(0.0, horizon, size=n_imm))
    queue = list(times)
    while queue:
        parent = queue.pop()
        k = int(rng.poisson(n))  # offspring count: Poisson(kernel integral = n)
        if k:
            for c in parent + rng.exponential(1.0 / beta, size=k):
                if c < horizon:
                    times.append(float(c))
                    queue.append(float(c))
    return np.sort(np.asarray(times, dtype=float))

"""The parrot null (Stage-2 belief-coupling-removed control). It is the COLLAPSE null: the same temporal
substrate as the coupled Deffuant control (news rate, Lomax delay-shape kernel, topology) with belief
coupling removed by taking the confidence bound to zero (BELIEF_FREE_EPS=0.0). With eps=0 no
|Δx|<eps success ever fires, so no offspring activate -> an immigrant-only stream, successes=0. Branching
is FREE TO COLLAPSE (not matched), which is exactly what makes 'does the reconstructed exponent survive'
informative rather than built-in. See docs/superpowers/specs/2026-06-25-parrot-null-design.md."""
from __future__ import annotations

from critaudit.sim.controls.deffuant import simulate_labeled
from critaudit.sim.controls.parrot_spec import BELIEF_FREE_EPS


def simulate_parrot(horizon, mu_news, *, N, k_reach, mu_step, kernel_eps, c, rng, max_events=500_000):
    """Collapse null via the shared generator at the zero confidence bound. Fail-closed: asserts the
    collapse actually happened (no offspring), so a future change to simulate_labeled that let an edge
    through at eps=0 is caught here rather than silently producing a non-null 'null'."""
    run = simulate_labeled(BELIEF_FREE_EPS, horizon, mu_news, N=N, k_reach=k_reach, mu_step=mu_step,
                           kernel_eps=kernel_eps, c=c, rng=rng, max_events=max_events)
    if run.successes != 0:
        raise AssertionError(f"parrot collapse failed: successes={run.successes} (expected 0 at eps=0)")
    return run

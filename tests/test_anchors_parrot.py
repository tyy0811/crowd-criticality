import numpy as np
import pytest
from critaudit.types import AvalancheSet
from critaudit.sim.controls.anchors import n_struct, burstiness, fano_profile


def test_n_struct_immigrant_only_is_zero():
    av = AvalancheSet(sizes=np.ones(5, np.int64), durations=np.ones(5, np.int64))
    assert n_struct(av) == 0.0


def test_n_struct_known_trees():
    # 3 trees, 6 events -> 1 - 3/6 = 0.5
    av = AvalancheSet(sizes=np.array([3, 1, 2], np.int64), durations=np.array([2, 1, 2], np.int64))
    assert n_struct(av) == pytest.approx(0.5)


def test_n_struct_empty_raises():
    av = AvalancheSet(sizes=np.array([], np.int64), durations=np.array([], np.int64))
    with pytest.raises(ValueError):
        n_struct(av)


def test_burstiness_regular_is_minus_one():
    t = np.arange(0.0, 100.0, 1.0)         # perfectly regular -> sigma=0 -> B=-1
    assert burstiness(t) == pytest.approx(-1.0)


def test_burstiness_poisson_near_zero_clustered_positive():
    rng = np.random.default_rng(0)
    poisson = np.sort(rng.uniform(0, 1000, size=4000))          # ~Poisson -> B≈0
    clumped = np.sort(np.concatenate([rng.uniform(0, 1, 2000),  # two tight clumps -> bursty
                                      rng.uniform(999, 1000, 2000)]))
    assert abs(burstiness(poisson)) < 0.2
    assert burstiness(clumped) > 0.5


def test_fano_profile_poisson_near_one_clustered_above():
    rng = np.random.default_rng(0)
    poisson = np.sort(rng.uniform(0, 1000, size=6000))
    clumped = np.sort(np.concatenate([rng.uniform(0, 50, 3000), rng.uniform(950, 1000, 3000)]))
    ws = (1000 / 50.0, 1000 / 10.0)
    fp = fano_profile(poisson, 1000.0, ws)
    fc = fano_profile(clumped, 1000.0, ws)
    assert fp.shape == (2,)
    assert np.all(fp < 2.0)                 # Poisson Fano ≈ 1
    assert np.nanmax(fc) > np.nanmax(fp)    # clustering inflates Fano

import numpy as np
import pytest
from critaudit.types import EventStream, AvalancheSet


def test_eventstream_valid():
    es = EventStream(times=[0.1, 0.2, 0.5], horizon=1.0)
    assert es.times.dtype == float and es.marks is None


def test_eventstream_rejects_non_increasing():
    with pytest.raises(ValueError):
        EventStream(times=[0.2, 0.2], horizon=1.0)


def test_eventstream_rejects_out_of_window():
    with pytest.raises(ValueError):
        EventStream(times=[0.1, 1.5], horizon=1.0)


def test_avalancheset_valid_and_censored():
    av = AvalancheSet(sizes=[1, 3, 2], durations=[1, 2, 2],
                      censored=[False, True, False])
    assert av.sizes.shape == (3,) and av.censored.dtype == bool


def test_avalancheset_rejects_bad_values():
    with pytest.raises(ValueError):
        AvalancheSet(sizes=[0, 1], durations=[1, 1])

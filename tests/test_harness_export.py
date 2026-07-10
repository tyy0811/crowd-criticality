import numpy as np
from critaudit.sim.harness.types import EventRecord, RefreshRecord
from critaudit.sim.harness.assemble import build_parent_root, assemble_harness_run
from critaudit.sim.controls.anchors import read_emit_ratio, n_struct
from critaudit.cascades.extract import post_reply_tree


def _events():
    # two trees: p0<-c1<-c2 (root 0), and a lone p3
    return [
        EventRecord("p0", 0.0, 0, None, "root a"),
        EventRecord("c1", 1.0, 1, "p0", "reply to p0"),
        EventRecord("p3", 1.5, 0, None, "root b"),
        EventRecord("c2", 2.0, 2, "c1", "reply to c1"),
    ]


def test_build_parent_root_shapes_and_invariants():
    times, root_id, parent_idx = build_parent_root(_events())
    assert np.allclose(times, [0.0, 1.0, 1.5, 2.0])
    assert parent_idx.tolist() == [-1, 0, -1, 1]
    assert root_id.tolist() == [0, 0, 2, 0]
    # feeds post_reply_tree without raising; sizes/durations as expected
    av = post_reply_tree(times, root_id, parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    assert sorted(av.durations.tolist()) == [1, 3]


def test_build_parent_root_unknown_parent_raises():
    bad = [EventRecord("c0", 0.0, 0, "missing", "x")]
    try:
        build_parent_root(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_assemble_and_read_emit_ratio_below_n_struct():
    events = _events()  # 4 events, 2 roots -> n_struct = 1 - 2/4 = 0.5
    refreshes = [RefreshRecord(1, 0.5, frozenset({"p0"}))]  # only c1 is a read->emit success
    run = assemble_harness_run(events, refreshes)
    assert run.times.size == 4
    assert run.content == ["root a", "reply to p0", "root b", "reply to c1"]
    av = post_reply_tree(run.times, run.root_id, run.parent_idx)
    assert sorted(av.sizes.tolist()) == [1, 3]
    assert read_emit_ratio(run) == 0.25
    assert read_emit_ratio(run) <= n_struct(av)      # the load-bearing inequality (accessibility, not crosses-1)


def test_read_emit_ratio_empty_raises():
    import numpy as np
    from critaudit.sim.harness.types import HarnessRun
    empty = HarnessRun(np.array([]), np.array([], np.int64), np.array([], np.int64),
                       np.array([], bool), [])
    try:
        read_emit_ratio(empty)
        assert False, "expected ValueError"
    except ValueError:
        pass

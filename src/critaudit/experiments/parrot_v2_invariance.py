"""Task 7 (Branch-B parrot-null v2 implementation plan, 2026-07-31): the INVARIANCE ORCHESTRATOR —
the one place the whole matched null is dispatched, retained and read out.

TWO ENTRY POINTS, ONE BODY. `run_invariance` is the REGISTERED PRODUCTION ENTRY and accepts nothing
but a work directory, a report path and an optional archive override: every experimental quantity it
uses — which schedules, which widths, which violator schedules, how long the whole thing may take —
is read from `parrot_v2_spec` at call time, so there is no argument through which a run could be
re-parameterized after registration. Running it is the separately-authorized measurement. All the
logic lives in `_run_invariance_core`, which takes those same quantities as injected arguments and a
`replay_runner` callable; that is the TEST SEAM, and it is private precisely so that the injectable
surface can never be mistaken for the registered one. A test pins `run_invariance`'s signature
exactly, so widening it is a loud break rather than a quiet re-parameterization.

THE FROZEN FAILURE PATH IS ONE PATH WITH THREE PROPERTIES (rev-5 spec; rev-2 blocker 3). Any run
failure — the child raising, a digest/read rejection, an echoed identity field that does not match
the envelope that was handed to the child, or a `graph_sha256` that diverges inside a width triple —
takes the SAME path:

  (a) DISPATCH STOPS IMMEDIATELY. No further replay is launched. A harness that keeps running after
      it has lost trust in one run spends the ceiling producing evidence nobody may use.
  (b) THE PARTIAL RESULT IS PERSISTED. The manifest is written over whatever artifacts exist, and an
      R3 `report.json` is written whose detail carries the VERBATIM failure string (via
      `overall_verdict(..., run_failures=(msg,))` — the ONLY place `run_failures` is ever fed). A
      failed run must leave MORE evidence behind than a successful one, not less.
  (c) `InvarianceFailure` IS RAISED. The caller never receives a value that looks like a reading.

Deadline expiry BEFORE the run directory exists is the one exception to (b): there is nothing
partial to persist, so it simply raises.

WHY `graph_sha256` IS CHECKED HERE AND NOT IN TASK 6. `build_follow_edges` is a pure function of the
schedule seed, so the three widths of one schedule MUST agree on the follow graph. A divergence means
the pairing was broken by something OTHER than the knob — which is a fact about the RUNS, not about
the payload comparison — so it is reported through this module's own `run_failures` channel in this
module's own words. Task 6's guard vocabulary is never string-matched here; the two failure
languages are kept separate on purpose so neither can drift into the other's meaning.

NON-CIRCULAR HASHING ORDER (the retention contract). Artifacts are written first (profile bytes,
envelope bytes, every replay output with its digest sidecar, every run database). THEN `manifest.json`
= `{relpath: sha256}` over every artifact in the run directory, with `manifest.json` and
`report.json` themselves excluded — a manifest that hashed itself could not be verified, and one that
hashed the report would forbid the report from naming the manifest. THEN `report.json`, which carries
`manifest_sha256` = the SHA-256 of the manifest's own bytes. The chain therefore runs
artifacts -> manifest -> report in one direction only. NOTHING IS EVER DELETED: the run directory is
invocation-unique (`run-<uuid4hex>`, created with `exist_ok=False` and required empty), so a second
invocation cannot land on the first one's evidence and no cleanup step is needed to keep them apart.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid

from critaudit.experiments.parrot_v2_replay import (
    REPLAY_PAYLOAD_KEYS,
    read_replay_output,
    run_replay_subprocess,
)
from critaudit.sim.controls import parrot_v2_profile, parrot_v2_spec
from critaudit.sim.controls.parrot_v2_compare import (
    manipulation_guard,
    overall_verdict,
    schedule_verdict,
    violator_verdict,
)
from critaudit.sim.controls.parrot_v2_schedule import build_schedule_envelope, envelope_to_bytes
from critaudit.sim.harness import harness_spec as hs

__all__ = ["InvarianceFailure", "run_invariance", "main"]


class InvarianceFailure(RuntimeError):
    """Raised for every condition under which an invariance run's output may not be read as a
    reading: an expired deadline, a profile set that is not the registered cohort, or any run
    failure (which additionally persists the partial manifest + R3 report first)."""


class _RunFailure(InvarianceFailure):
    """Internal marker: a failure whose message is ALREADY the final, verbatim failure string, so
    the persistence handler must not re-wrap it with a second context prefix."""


# --- deadline ---------------------------------------------------------------------------------

class _Deadline:
    """A monotonic deadline. `time.monotonic` is used rather than wall clock because the ceiling is
    a compute budget, not a calendar time: a clock adjustment mid-run must not extend or collapse
    it. `remaining` is what each child is given as its own timeout, so no child can outlive the
    budget the orchestrator is holding it to."""

    def __init__(self, ceiling_seconds):
        self.ceiling_seconds = float(ceiling_seconds)
        self.started = time.monotonic()
        self.expires_at = self.started + self.ceiling_seconds

    def remaining(self) -> float:
        return self.expires_at - time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def check(self, stage):
        """Fail closed at a stage boundary. `<= 0` rather than `< 0` so a zero ceiling is expired at
        its first check regardless of clock granularity."""
        left = self.remaining()
        if left <= 0:
            raise _RunFailure(
                f"invariance deadline exceeded at {stage}: ceiling {self.ceiling_seconds:.0f}s, "
                f"elapsed {self.elapsed():.1f}s (fail-closed)")
        return left


# --- canonical JSON artifacts -------------------------------------------------------------------

def _canonical_bytes(payload) -> bytes:
    """The run-codec house pattern (sorted keys, compact separators, trailing newline). The manifest
    is hashed as BYTES by the report, so its serialization must be canonical rather than incidental."""
    return (
        json.dumps(payload, allow_nan=False, ensure_ascii=False, separators=(",", ":"),
                   sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _write_bytes(path, data: bytes) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(run_dir, *, report_path) -> tuple:
    """`{relpath: sha256}` over EVERY file in the run directory, excluding the manifest and the
    report themselves (see the module docstring's hashing order). Returns (manifest_path, bytes)."""
    manifest_path = os.path.join(run_dir, "manifest.json")
    excluded = {os.path.abspath(manifest_path), os.path.abspath(report_path)}
    entries = {}
    for root, _dirs, files in os.walk(run_dir):
        for name in sorted(files):
            path = os.path.join(root, name)
            if os.path.abspath(path) in excluded:
                continue
            entries[os.path.relpath(path, run_dir)] = _sha256_file(path)
    data = _canonical_bytes(entries)
    _write_bytes(manifest_path, data)
    return manifest_path, data


def _write_report(report_path, payload) -> bytes:
    data = _canonical_bytes(payload)
    _write_bytes(report_path, data)
    return data


# --- failure formatting -------------------------------------------------------------------------

def _child_stderr(exc) -> str:
    """A child's stderr, folded in whatever form the subprocess machinery attached it. Without this
    a `CalledProcessError` reduces to its exit status, and the actual traceback that explains the
    failure — the one the persisted report exists to preserve — is lost."""
    stream = getattr(exc, "stderr", None)
    if not stream:
        return ""
    if isinstance(stream, bytes):
        stream = stream.decode("utf-8", errors="replace")
    return str(stream)


def _failure_message(context, exc) -> str:
    if isinstance(exc, _RunFailure):
        return str(exc)                      # already the final, verbatim string
    text = f"{context}: {type(exc).__name__}: {exc}"
    stderr = _child_stderr(exc)
    if stderr:
        text += f" | child stderr: {stderr.strip()}"
    return text


# --- identity cross-checks ------------------------------------------------------------------------

def _crosscheck_identity(payload, envelope, *, run_key, width, violator):
    """Every identity field the child ECHOED must match the envelope the child was handed. The child
    is a separate process reading a file off disk; without this, a stale output left by an earlier
    invocation, or an envelope/width pairing that got crossed in dispatch, would be read as this
    run's result. The digest sidecar proves the bytes are intact, never that they are the RIGHT
    bytes — that is what these checks are for."""
    if set(payload) != set(REPLAY_PAYLOAD_KEYS):
        raise _RunFailure(
            f"run {run_key}: replay payload key set {sorted(payload)!r} is not the pinned "
            f"REPLAY_PAYLOAD_KEYS {sorted(REPLAY_PAYLOAD_KEYS)!r} (fail-closed)")
    expected = {
        "schedule_seed": int(envelope.schedule_seed),
        "assigned_window": int(envelope.assigned_window),
        "profile_sha256": envelope.profile_sha256,
        "platform_seed": int(envelope.platform_seed),
        "schedule_sha256": envelope.schedule_sha256,
        "width": int(width),
        "violator": bool(violator),
    }
    for key, want in expected.items():
        got = payload[key]
        if type(want) is bool:
            got = bool(got)
        elif isinstance(want, int):
            got = int(got)
        if got != want:
            raise _RunFailure(
                f"run {run_key}: replay echoed {key}={payload[key]!r} but the dispatched envelope "
                f"says {want!r} (fail-closed identity mismatch)")


def _crosscheck_graph(payload, *, run_key, reference, reference_key):
    """The paired-graph provenance: `build_follow_edges` is a pure function of the schedule seed, so
    every width of one schedule must report the SAME `graph_sha256`. A divergence means the pairing
    was broken by something other than the recommender width, which invalidates the comparison the
    triple exists to support."""
    graph_sha = payload["graph_sha256"]
    if reference is not None and graph_sha != reference:
        raise _RunFailure(
            f"run {run_key}: graph_sha256 {graph_sha!r} diverges from {reference!r} at "
            f"{reference_key} — the paired follow graph is not shared across the width triple "
            f"(fail-closed)")
    return graph_sha


# --- the core (test seam) -------------------------------------------------------------------------

def _run_key(*, schedule_seed, width, violator) -> str:
    return f"{'violator' if violator else 'schedule'}-{int(schedule_seed)}-w{int(width)}"


def _run_invariance_core(work_dir, report_path, *, profiles, schedule_seeds, widths,
                         violator_seeds, ceiling_seconds, replay_runner) -> dict:
    """The whole orchestration, with every experimental quantity injected. See the module docstring:
    the ordering below (deadline -> profile validation -> unique run dir -> artifacts -> dispatch ->
    manifest -> report) IS the contract, and the `except` block below is the one frozen failure
    path."""
    deadline = _Deadline(ceiling_seconds)
    deadline.check("start")                       # nothing exists yet: expiry here simply raises

    registered = set(hs.COHORT_SEEDS)
    if set(profiles) != registered:
        raise InvarianceFailure(
            f"invariance profile set {sorted(profiles)!r} is not the registered cohort window set "
            f"{sorted(registered)!r} — one action profile per registered window, exactly "
            f"(fail-closed)")

    os.makedirs(work_dir, exist_ok=True)
    run_dir = os.path.join(work_dir, f"run-{uuid.uuid4().hex}")
    os.makedirs(run_dir, exist_ok=False)          # invocation-unique: never reuses an existing dir
    if os.listdir(run_dir):
        raise InvarianceFailure(
            f"invariance run directory {run_dir!r} is not empty immediately after creation "
            f"(fail-closed)")

    schedule_seeds = tuple(int(s) for s in schedule_seeds)
    widths = tuple(int(w) for w in widths)
    violator_seeds = tuple(int(s) for s in violator_seeds)

    schedule_verdicts = []
    violator_verdicts = []
    schedule_records = []
    violator_records = []
    read_emit_ratio = {}
    run_timings = {}
    timings = {}
    dispatch_started = None

    try:
        # (1) artifacts: profile bytes, then one envelope per schedule seed.
        deadline.check("profile serialization")
        stage_started = time.monotonic()
        for window_seed in sorted(profiles):
            _write_bytes(
                os.path.join(run_dir, "profiles", f"profile-{window_seed}.json"),
                parrot_v2_profile.profile_to_bytes(profiles[window_seed]))
        timings["profiles_s"] = time.monotonic() - stage_started

        deadline.check("envelope generation")
        stage_started = time.monotonic()
        envelopes = {}
        envelope_paths = {}
        for schedule_seed in schedule_seeds:
            window = parrot_v2_spec.assigned_window(schedule_seed)
            envelope = build_schedule_envelope(profiles[window], schedule_seed)
            path = os.path.join(run_dir, "envelopes", f"envelope-{schedule_seed}.json")
            _write_bytes(path, envelope_to_bytes(envelope))
            envelopes[schedule_seed] = envelope
            envelope_paths[schedule_seed] = path
        timings["envelopes_s"] = time.monotonic() - stage_started

        # (2) dispatch: the invariance arm, then the violator arm. Every run is preceded by a
        #     deadline check and hands the child the remaining budget as its own timeout.
        dispatch_started = time.monotonic()
        for violator, seeds in ((False, schedule_seeds), (True, violator_seeds)):
            deadline.check(f"{'violator' if violator else 'invariance'} arm")
            for schedule_seed in seeds:
                triple = {}
                graph_reference = None
                graph_reference_key = None
                for width in widths:
                    run_key = _run_key(
                        schedule_seed=schedule_seed, width=width, violator=violator)
                    left = deadline.check(f"run {run_key}")
                    run_subdir = os.path.join(run_dir, "runs", run_key)
                    os.makedirs(run_subdir, exist_ok=True)
                    out_path = os.path.join(run_subdir, "replay.json")
                    database_path = os.path.join(run_subdir, "oasis.db")

                    started = time.monotonic()
                    replay_runner(
                        envelope_paths[schedule_seed],
                        width=width,
                        database_path=database_path,
                        out_path=out_path,
                        violator=violator,
                        timeout=left)
                    payload = read_replay_output(out_path)     # digest-verified before decoding
                    run_timings[run_key] = time.monotonic() - started

                    _crosscheck_identity(
                        payload, envelopes[schedule_seed],
                        run_key=run_key, width=width, violator=violator)
                    graph_sha = _crosscheck_graph(
                        payload, run_key=run_key,
                        reference=graph_reference, reference_key=graph_reference_key)
                    if graph_reference is None:
                        graph_reference, graph_reference_key = graph_sha, run_key

                    # read_emit_ratio is DESCRIPTIVE only (Task 6 keeps it out of equality); it is
                    # recorded per run so an exposure diagnostic is available without ever having
                    # been able to influence a verdict.
                    read_emit_ratio[run_key] = payload["observables"]["read_emit_ratio"]
                    triple[width] = payload

                deadline.check(f"verdict for schedule {schedule_seed}")
                if violator:
                    verdict = violator_verdict(triple)
                    violator_verdicts.append(verdict)
                    violator_records.append({
                        "schedule_seed": schedule_seed,
                        "graph_sha256": graph_reference,
                        "guard": manipulation_guard(triple),
                        "ok": verdict["ok"],
                        "reason": verdict["reason"]})
                else:
                    verdict = schedule_verdict(triple)
                    schedule_verdicts.append(verdict)
                    schedule_records.append({
                        "schedule_seed": schedule_seed,
                        "assigned_window": int(envelopes[schedule_seed].assigned_window),
                        "schedule_sha256": envelopes[schedule_seed].schedule_sha256,
                        "graph_sha256": graph_reference,
                        "invariant": verdict["invariant"],
                        "first_divergence": verdict["first_divergence"],
                        "guard": verdict["guard"]})
        timings["runs_s"] = time.monotonic() - dispatch_started

        deadline.check("verdict assembly")
        overall = overall_verdict(schedule_verdicts, violator_verdicts)
        run_failures = ()
    except Exception as exc:                       # THE frozen failure path — (a), (b), (c)
        message = _failure_message("invariance run failed", exc)
        run_failures = (message,)
        overall = overall_verdict((), (), run_failures=run_failures)
        if dispatch_started is not None and "runs_s" not in timings:
            timings["runs_s"] = time.monotonic() - dispatch_started
        timings["total_s"] = deadline.elapsed()
        _finalize(run_dir, report_path, overall=overall, timings=timings,
                  schedule_records=schedule_records, violator_records=violator_records,
                  read_emit_ratio=read_emit_ratio, run_timings=run_timings,
                  run_failures=run_failures, deadline=deadline,
                  schedule_seeds=schedule_seeds, widths=widths, violator_seeds=violator_seeds)
        raise InvarianceFailure(message) from exc

    timings["total_s"] = deadline.elapsed()
    report = _finalize(run_dir, report_path, overall=overall, timings=timings,
                       schedule_records=schedule_records, violator_records=violator_records,
                       read_emit_ratio=read_emit_ratio, run_timings=run_timings,
                       run_failures=run_failures, deadline=deadline,
                       schedule_seeds=schedule_seeds, widths=widths, violator_seeds=violator_seeds)
    return {"reading": report["reading"], "detail": report["detail"], "run_dir": run_dir,
            "report_path": report_path, "manifest_sha256": report["manifest_sha256"],
            "schedules": schedule_records, "violators": violator_records}


def _finalize(run_dir, report_path, *, overall, timings, schedule_records, violator_records,
              read_emit_ratio, run_timings, run_failures, deadline, schedule_seeds, widths,
              violator_seeds) -> dict:
    """The hashing order, in one place so the success path and the failure path cannot diverge on
    it: artifacts (already written) -> manifest -> report carrying the manifest's own digest."""
    _manifest_path, manifest_bytes = _write_manifest(run_dir, report_path=report_path)
    report = {
        "schema": parrot_v2_spec.SCHEMA,
        "reading": overall["reading"],
        "detail": overall["detail"],
        "run_dir": run_dir,
        "run_failures": list(run_failures),
        "schedules": schedule_records,
        "violators": violator_records,
        "read_emit_ratio": read_emit_ratio,          # descriptive, never part of any verdict
        "timings": dict(timings, per_run_s=run_timings),
        "spec": {
            "schedule_seeds": list(schedule_seeds),
            "widths": list(widths),
            "violator_seeds": list(violator_seeds),
            "ceiling_seconds": deadline.ceiling_seconds,
        },
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    _write_report(report_path, report)
    return report


# --- the registered production entry --------------------------------------------------------------

def _resolve_profiles(archive_dir=None) -> dict:
    """One `CohortActionProfile` per REGISTERED cohort window, extracted from the archive's trace
    databases. Path resolution is delegated (`parrot_v2_profile.archive_window_db_path`, itself a
    delegate of `llm_parrot_null`) so the archive layout keeps exactly one owner."""
    profiles = {}
    for window_seed in hs.COHORT_SEEDS:
        if archive_dir is None:
            db_path = parrot_v2_profile.archive_window_db_path(window_seed)
        else:
            from critaudit.experiments.llm_parrot_null import _window_db
            db_path = _window_db(archive_dir, window_seed)
        profiles[window_seed] = parrot_v2_profile.extract_action_profile(
            db_path, window_seed=window_seed)
    return profiles


def run_invariance(work_dir, report_path, *, archive_dir=None) -> dict:
    """THE REGISTERED ENTRY. Its signature is frozen and pinned by a test: there is deliberately no
    argument for the schedules, the widths, the violator schedules or the ceiling, because those are
    registered quantities read from `parrot_v2_spec` here and nowhere else. Calling this is the
    separately-authorized measurement."""
    return _run_invariance_core(
        work_dir, report_path,
        profiles=_resolve_profiles(archive_dir),
        schedule_seeds=parrot_v2_spec.SCHEDULE_SEEDS,
        widths=parrot_v2_spec.WIDTHS,
        violator_seeds=parrot_v2_spec.VIOLATOR_SCHEDULE_SEEDS,
        ceiling_seconds=parrot_v2_spec.CEILING_SECONDS,
        replay_runner=run_replay_subprocess)


def main(argv=None):
    """CLI over the PRODUCTION entry only — the injected core is not reachable from here."""
    parser = argparse.ArgumentParser(
        description="Run the parrot-null v2 recommender-width invariance measurement.")
    parser.add_argument("--work-dir", required=True, help="parent directory for the run directory")
    parser.add_argument("--report", required=True, help="path for the run's report.json")
    parser.add_argument("--archive-dir", default=None,
                        help="registered-archive root (default: the registered archive)")
    args = parser.parse_args(argv)
    result = run_invariance(args.work_dir, args.report, archive_dir=args.archive_dir)
    print(json.dumps({"reading": result["reading"], "run_dir": result["run_dir"],
                      "report_path": result["report_path"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    main()

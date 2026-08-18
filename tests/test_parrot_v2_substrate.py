# tests/test_parrot_v2_substrate.py
"""Pins the OASIS facts the parrot-v2 rig relies on (read-verified 2026-07-31;
these tests make the pins executable). Direct-PLATFORM calls here use the
platform tuple signatures (sign_up((user_name, name, bio)); create_comment /
quote_post take one tuple arg at platform level); the replayer (Task 5) uses
the two-arg AGENT action path instead. All tiny, all $0, @slow."""
import asyncio, sqlite3, pytest

pytestmark = pytest.mark.slow


def _tiny_platform(tmp_path, width, name="probe"):
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType
    from oasis.social_platform.channel import Channel
    return Platform(
        db_path=str(tmp_path / f"{name}_{width}.db"), channel=Channel(),
        recsys_type=RecsysType("random"), refresh_rec_post_count=width,
        max_rec_post_len=5, following_post_count=3)


async def _sign_up(p, *uids):
    for uid in uids:
        r = await p.sign_up(uid, (f"u{uid}", f"u{uid}", ""))   # TUPLE signature
        assert r["success"] is True


def test_clock_initializes_at_zero(tmp_path):
    p = _tiny_platform(tmp_path, 3)
    assert p.sandbox_clock.time_step == 0          # Clock.__init__ (clock.py)
    p.sandbox_clock.time_step += 1                 # mutable int, our own increment
    assert p.sandbox_clock.time_step == 1


def test_action_return_keys_and_namespaces(tmp_path):
    """create_post/quote_post/repost -> 'post_id'; create_comment -> 'comment_id'.
    The repost is made by a SECOND agent: agent 0's earlier quote of t writes
    original_post_id == t, so agent 0's own repost of t would be a duplicate."""
    async def go():
        p = _tiny_platform(tmp_path, 3)
        await _sign_up(p, 0, 1)
        r1 = await p.create_post(0, "hello")
        assert r1["success"] is True and "post_id" in r1
        t = int(r1["post_id"])
        r2 = await p.create_comment(0, (t, "c"))
        assert r2["success"] is True and "comment_id" in r2
        r3 = await p.quote_post(0, (t, "q"))
        assert r3["success"] is True and "post_id" in r3
        r4 = await p.repost(1, t)                   # SECOND agent
        assert r4["success"] is True and "post_id" in r4
    asyncio.run(go())


def test_empty_refresh_returns_no_posts_and_writes_no_trace(tmp_path):
    async def go():
        p = _tiny_platform(tmp_path, 3)
        await _sign_up(p, 0)
        r = await p.refresh(0)                     # rec table empty, no follows
        assert r["success"] is False and r.get("message") == "No posts found."
        con = sqlite3.connect(p.db_path)
        n = con.execute(
            "SELECT COUNT(*) FROM trace WHERE action='refresh'").fetchone()[0]
        con.close()
        assert n == 0                              # empty path records NO trace row
    asyncio.run(go())


def test_repost_duplicate_two_clause_predicate(tmp_path):
    """Clause 1 incl. prior QUOTES; clause 2 root-resolution for repost targets."""
    async def go():
        p = _tiny_platform(tmp_path, 3)
        await _sign_up(p, 0, 1, 2)
        t = int((await p.create_post(0, "root"))["post_id"])
        # clause 1: agent 1's QUOTE of t blocks agent 1's repost of t
        assert (await p.quote_post(1, (t, "q")))["success"] is True
        dup = await p.repost(1, t)
        assert dup["success"] is False and "already exists" in dup["error"]
        # clause 2: agent 2 reposts t -> rp; agent 2 cannot repost rp (root u == t)
        rp = int((await p.repost(2, t))["post_id"])
        dup2 = await p.repost(2, rp)
        assert dup2["success"] is False and "already exists" in dup2["error"]
    asyncio.run(go())


def test_written_original_resolution(tmp_path):
    """Pins the written original_post_id table the Task-4 bookkeeping mirrors:
      repost of common/quote target -> t itself;  repost of repost -> target's root
      quote  of common            -> t itself;    quote of repost/quote -> target's root."""
    async def go():
        p = _tiny_platform(tmp_path, 3)
        await _sign_up(p, 0, 1, 2, 3)
        t = int((await p.create_post(0, "root"))["post_id"])
        q = int((await p.quote_post(1, (t, "q1")))["post_id"])      # quote of common
        rp = int((await p.repost(2, t))["post_id"])                  # repost of common
        q_of_rp = int((await p.quote_post(3, (rp, "q2")))["post_id"])  # quote of repost
        rp_of_q = int((await p.repost(3, q))["post_id"])             # repost of quote
        con = sqlite3.connect(p.db_path)
        orig = dict(con.execute(
            "SELECT post_id, original_post_id FROM post "
            "WHERE original_post_id IS NOT NULL").fetchall())
        con.close()
        assert orig[q] == t              # quote of common -> t
        assert orig[rp] == t             # repost of common -> t
        assert orig[q_of_rp] == t        # quote of REPOST -> ROOT-resolved
        assert orig[rp_of_q] == q        # repost of QUOTE -> the quote id ITSELF
    asyncio.run(go())


def test_refresh_serves_and_traces_when_posts_exist(tmp_path):
    async def go():
        p = _tiny_platform(tmp_path, 1)
        await _sign_up(p, 0, 1)
        for k in range(4):
            await p.create_post(0, f"p{k}")
        await p.update_rec_table()
        r = await p.refresh(1)                      # no follows -> rec sample only
        assert r["success"] is True
        assert len(r["posts"]) <= 1 + 3             # width 1 + following_post_count cap
        assert "post_id" in r["posts"][0]           # served payload key (violator hashes it)
    asyncio.run(go())

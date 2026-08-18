# tests/test_parrot_v2_profile.py
import asyncio, pytest
from critaudit.sim.controls.parrot_v2_profile import (
    COHORT_ACTION_PROFILE_FIELDS, CohortActionProfile, extract_action_profile,
    profile_from_bytes, profile_sha256, profile_to_bytes)


def test_whitelist_field_set_pinned():
    assert COHORT_ACTION_PROFILE_FIELDS == (
        "window_seed", "per_round_type_counts", "per_round_refresh_counts",
        "news_events", "authored_corpus")


@pytest.fixture(scope="module")
def synthetic_db(tmp_path_factory):
    """Tiny real-OASIS DB with known composition: rounds 0-1; news post at round 1;
    round-0 crowd create_post; round-1 comment+repost+quote; 1 traced refresh."""
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import RecsysType
    from oasis.social_platform.channel import Channel
    db = str(tmp_path_factory.mktemp("prof") / "syn.db")
    async def build():
        p = Platform(db_path=db, channel=Channel(), recsys_type=RecsysType("random"),
                     refresh_rec_post_count=3, max_rec_post_len=5,
                     following_post_count=3)
        for uid in (0, 1, 50):        # 50 = NEWS_USER_AGENT_ID
            await p.sign_up(uid, (f"u{uid}", f"u{uid}", ""))     # TUPLE signature
        assert p.sandbox_clock.time_step == 0
        t = int((await p.create_post(0, "crowd root"))["post_id"])     # round 0
        await p.update_rec_table()
        r = await p.refresh(1)                                          # traced refresh
        assert r["success"] is True
        p.sandbox_clock.time_step += 1                                  # round 1
        await p.create_comment(1, (t, "a comment"))
        await p.repost(1, t)
        await p.quote_post(0, (t, "a quote"))
        await p.create_post(50, "NEWS ITEM")                            # news, round 1
        return db
    return asyncio.run(build())


@pytest.mark.slow
def test_extraction_counts_news_adjust_and_corpus(synthetic_db):
    prof = extract_action_profile(synthetic_db, window_seed=999)
    assert prof.window_seed == 999
    assert prof.per_round_type_counts[0] == (1, 0, 0, 0)
    # round 1 news-adjusted: the only round-1 create_post row IS the news event
    assert prof.per_round_type_counts[1] == (0, 1, 1, 1)
    assert prof.per_round_refresh_counts == (1, 0)
    assert prof.news_events == ((1, "NEWS ITEM"),)
    assert sorted(prof.authored_corpus) == ["a comment", "a quote", "crowd root"]
    # repost '' and news text are EXCLUDED from the corpus


@pytest.mark.slow
def test_codec_roundtrip_and_tamper(synthetic_db):
    prof = extract_action_profile(synthetic_db, window_seed=999)
    data = profile_to_bytes(prof)
    assert profile_from_bytes(data) == prof
    assert len(profile_sha256(prof)) == 64
    with pytest.raises(ValueError):
        profile_from_bytes(data + b" ")

from app.services.trending_filter import is_trending_worthy_query


def test_accepts_normal_news_query():
    assert is_trending_worthy_query("what is happening in ukraine?") is True


def test_rejects_short_and_blocklisted_queries():
    assert is_trending_worthy_query("hi") is False
    assert is_trending_worthy_query("test chat") is False
    assert is_trending_worthy_query("nonsense query") is False


def test_rejects_long_transcript_like_queries():
    transcript = (
        "welcome to the made by google podcast, where we meet the people who work on "
        "the google products you love. here's your host, rashid finch."
    )
    assert is_trending_worthy_query(transcript) is False


def test_rejects_smoke_test_hex_suffixes():
    assert is_trending_worthy_query("quantum entanglement breakthrough d73a76ae") is False
    assert is_trending_worthy_query("mars colony update f7a68ffd") is False


def test_rejects_known_fixture_terms():
    assert is_trending_worthy_query("zorbax crystal reactor accident 2026") is False

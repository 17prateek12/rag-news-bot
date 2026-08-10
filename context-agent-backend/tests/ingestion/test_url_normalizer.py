from app.ingestion.url_normalizer import normalize_url


def test_normalize_url_strips_tracking_and_fragment():
    raw = (
        "https://www.bbc.co.uk/news/articles/c980j3j578do"
        "?at_medium=RSS&at_campaign=rss#section"
    )
    assert normalize_url(raw) == "https://www.bbc.co.uk/news/articles/c980j3j578do"


def test_normalize_url_strips_ndtv_fragment():
    raw = (
        "https://www.ndtv.com/india-news/example-11880831"
        "#publisher=newsstand"
    )
    assert normalize_url(raw) == "https://www.ndtv.com/india-news/example-11880831"

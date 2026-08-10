from app.services.trending_topic import extract_trending_topic, format_topic_label


def test_extracts_country_from_question():
    assert extract_trending_topic("what is happening in ukraine?") == "ukraine"
    assert format_topic_label("ukraine") == "Ukraine"


def test_extracts_short_topic_from_long_query():
    assert extract_trending_topic("spacex starship launch august 2026 latest update") == "spacex starship launch"


def test_extracts_policy_topic():
    assert extract_trending_topic("latest news about education policy in india") == "education policy india"


def test_preserves_protest_topic():
    assert extract_trending_topic("jharkhand protest updates") == "jharkhand protest"
    assert format_topic_label("jharkhand protest") == "Jharkhand Protest"

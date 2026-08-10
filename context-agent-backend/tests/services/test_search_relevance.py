from app.services.search_relevance import filter_hits_by_topic, hit_matches_topic


def test_ukraine_requires_ukraine_terms():
    ukraine_hit = {
        "title": "Child among three killed in Russian missile attacks near Kyiv",
        "chunk": "Russia continued attacks after Zelensky warned of dwindling supplies.",
    }
    unrelated_hit = {
        "title": "Saudi Arabia, Turkey and Pakistan sign defence pact",
        "chunk": "Pakistan says an attack on any of the three will amount to an attack against all.",
    }
    assert hit_matches_topic("ukraine", ukraine_hit) is True
    assert hit_matches_topic("ukraine", unrelated_hit) is False


def test_multi_word_topic_uses_specific_terms():
    jharkhand_hit = {"title": "Protests spread across Jharkhand", "chunk": "Demonstrators blocked roads."}
    generic_hit = {"title": "Protests spread in capital", "chunk": "Demonstrators blocked roads."}
    assert hit_matches_topic("jharkhand protest", jharkhand_hit) is True
    assert hit_matches_topic("jharkhand protest", generic_hit) is False


def test_filter_drops_unrelated_hits():
    hits = [
        {"title": "War in Ukraine intensifies", "chunk": "Ukrainian forces..."},
        {"title": "Serbian eagle rescued", "chunk": "Wildlife officials..."},
    ]
    filtered = filter_hits_by_topic("ukraine", hits)
    assert len(filtered) == 1
    assert "Ukraine" in filtered[0]["title"]

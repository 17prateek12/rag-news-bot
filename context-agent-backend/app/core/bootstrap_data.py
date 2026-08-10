"""Default categories and RSS feeds — single source of truth for bootstrap."""

CATEGORIES = [
    "Top Stories",
    "India",
    "World",
    "Science & Tech",
    "Politics",
    "Business",
    "Sports",
    "Environment",
    "Entertainment",
    "Opinion",
]

RSS_FEEDS = [
    {
        "source": "BBC",
        "category": "World",
        "feed_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "BBC",
        "category": "Politics",
        "feed_url": "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "BBC",
        "category": "Business",
        "feed_url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "BBC",
        "category": "Science & Tech",
        "feed_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "BBC",
        "category": "Environment",
        "feed_url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "BBC",
        "category": "Top Stories",
        "feed_url": "https://feeds.bbci.co.uk/news/rss.xml",
        "parser_key": "bbc",
    },
    {
        "source": "NDTV",
        "category": "India",
        "feed_url": "https://feeds.feedburner.com/ndtvnews-india-news",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "Top Stories",
        "feed_url": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "Science & Tech",
        "feed_url": "https://feeds.feedburner.com/gadgets360-latest",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "Business",
        "feed_url": "https://feeds.feedburner.com/ndtvprofit-latest",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "World",
        "feed_url": "https://feeds.feedburner.com/ndtvnews-world-news",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "Sports",
        "feed_url": "https://feeds.feedburner.com/ndtvsports-latest",
        "parser_key": "ndtv",
    },
    {
        "source": "NDTV",
        "category": "Entertainment",
        "feed_url": "https://feeds.feedburner.com/ndtvmovies-latest",
        "parser_key": "ndtv",
    },
    {
        "source": "Hindu",
        "category": "India",
        "feed_url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "World",
        "feed_url": "https://www.thehindu.com/news/international/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "Business",
        "feed_url": "https://www.thehindu.com/business/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "Science & Tech",
        "feed_url": "https://www.thehindu.com/sci-tech/science/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "Entertainment",
        "feed_url": "https://www.thehindu.com/entertainment/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "Sports",
        "feed_url": "https://www.thehindu.com/sport/feeder/default.rss",
        "parser_key": "hindu",
    },
    {
        "source": "Hindu",
        "category": "Opinion",
        "feed_url": "https://www.thehindu.com/opinion/feeder/default.rss",
        "parser_key": "hindu",
    },
]

VALID_PARSER_KEYS = {"bbc", "ndtv", "hindu"}

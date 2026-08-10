from app.ingestion.parsers.base import BaseFeedParser
from app.ingestion.parsers.bbc_parser import BBCParser
from app.ingestion.parsers.hindu_parser import HinduParser
from app.ingestion.parsers.ndtv_parser import NDTVParser


class ParserRegistry:
    _parsers: dict[str, BaseFeedParser] = {
        "bbc": BBCParser(),
        "ndtv": NDTVParser(),
        "hindu": HinduParser(),
    }

    @classmethod
    def get(cls, parser_key: str) -> BaseFeedParser:
        parser = cls._parsers.get(parser_key.lower())
        if not parser:
            raise ValueError(f"No parser registered for key: {parser_key}")
        return parser

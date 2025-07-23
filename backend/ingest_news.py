from newspaper import Article
from langchain_community.embeddings import JinaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import feedparser

from config import QDRANT_URL, JINA_API_KEY

qdrant = QdrantClient(url=QDRANT_URL)
embedding_model = JinaEmbeddings(api_key=JINA_API_KEY, model_name="jina-embeddings-v2-base-en")
COLLECTION_NAME = "news_article"

def init_collection():
    """Create collection if it doesn't exist."""
    collections = [col.name for col in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        print(f"Collection '{COLLECTION_NAME}' created.")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists.")

def fetch_articles_from_rss(feed_url):
    """Fetch and parse articles from an RSS feed using newspaper3k."""
    feed = feedparser.parse(feed_url)
    print(f"Found {len(feed.entries)} entries in the RSS feed")

    articles = []
    for entry in feed.entries:
        print(f"Trying: {entry.link}")
        try:
            article = Article(entry.link)
            article.download()
            article.parse()
            if article.text:
                print(f"{article.title}")
                articles.append({
                    "title": article.title,
                    "url": entry.link,
                    "text": article.text
                })
            else:
                print(f"Skipped (too short or empty): {entry.link}")
        except Exception as e:
            print(f"Error: {e}")
    print(f"Total articles fetched: {len(articles)}\n")
    return articles

def embed_and_store_article(articles):
    """Embed article content and store in Qdrant."""
    points = []
    for article in articles:
        try:
            print(f"Embedding: {article['title']}")
            vector = embedding_model.embed_documents([article["text"]])[0]
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    'title': article["title"],
                    'url': article["url"],
                    'text': article["text"][:1000]
                }
            )
            points.append(point)
        except Exception as e:
            print(f"Embedding failed for: {article['title']}\nError: {e}")

    if points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"Stored {len(points)} articles in Qdrant.")
    else:
        print("No valid articles to store.")

#if __name__ == '__main__':
#    init_collection()
#    print("Running news fetch test...")
#
#    # Change RSS feed URL here if needed
#    rss_url = "https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"
#    articles = fetch_articles_from_rss(rss_url)
#
#    if not articles:
#        print("No articles were fetched. Check if RSS or parsing is failing.")
#    else:
#        print(f"{len(articles)} articles fetched:")
#        for a in articles:
#            print(f"\n Title: {a['title']}\n URL: {a['url']}\n Text: {a['text'][:200]}...\n")
#
#        embed_and_store_article(articles)
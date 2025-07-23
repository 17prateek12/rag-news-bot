from qdrant_client import QdrantClient
from langchain_community.embeddings import JinaEmbeddings
from google import genai
from config import QDRANT_URL, JINA_API_KEY, GEMINI_API_KEY

qdrant = QdrantClient(url=QDRANT_URL)
embedding_model = JinaEmbeddings(api_key=JINA_API_KEY, model_name="jina-embeddings-v2-base-en")

API_KEY=GEMINI_API_KEY
client = genai.Client(api_key=API_KEY)

Collection_Name = "news_article"

def get_top_k_passage(query: str, k: int = 5):
    vector = embedding_model.embed_query(query)
    search = qdrant.search(
        collection_name=Collection_Name,
        query_vector=vector,
        limit=k
    )
    return [hit.payload['text'] for hit in search]

def generate_answer(query:str):
    contexts = get_top_k_passage(query)
    if not contexts:
        return "Sorry, I couldn't find relevant news context for your query."
    
    response = client.models.generate_content(
        
        model='gemini-2.0-flash',
        contents = f"""Answer the question based on the news context below:

Context:
{chr(10).join(contexts)}

Question:
{query}
"""
    )
    return response.text
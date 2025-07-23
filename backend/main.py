from fastapi import FastAPI,  HTTPException, WebSocket
from pydantic import BaseModel
from rag_pipeline import generate_answer
from chat_manager import create_session, delete_session, get_history, append_message
from ingest_news import  init_collection
from contextlib import asynccontextmanager
from websocket_handler import handle_websocket
from ingest_news import embed_and_store_article, fetch_articles_from_rss
from fastapi.middleware.cors import CORSMiddleware
from scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app):
    init_collection()

    rss_url = "https://rss.app/feeds/z7n3qo1xCm03NWsq.xml"
    print(f"Fetching articles from: {rss_url}")
    articles = fetch_articles_from_rss(rss_url)

    if articles:
        print(f"{len(articles)} articles fetched. Storing embeddings...")
        embed_and_store_article(articles)
        print("Articles embedded and stored.")
    else:
        print("No articles were fetched from the RSS feed.")

    start_scheduler()  # Start the periodic job scheduler

    yield

#@asynccontextmanager
#async def lifespan(app):
#    init_collection()
#    
#    rss_url = "https://rss.app/feeds/z7n3qo1xCm03NWsq.xml"
#    print(f"Fetching articles from: {rss_url}")
#    articles = fetch_articles_from_rss(rss_url)
#
#    if articles:
#        print(f"{len(articles)} articles fetched. Storing embeddings...")
#        embed_and_store_article(articles)
#        print("Articles embedded and stored.")
#    else:
#        print("No articles were fetched from the RSS feed.")
#
#    yield  

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class Message(BaseModel):
    session_id: str
    query: str
    
    
@app.websocket('/ws/{session_id}')
async def websocket_endpoint(websocket:WebSocket, session_id:str):
    await handle_websocket(websocket,session_id)
    
@app.post('/chat')    
def chat(message:Message):
    session_id = message.session_id
    query = message.query
    append_message(session_id, "user", query)
    answer = generate_answer(query)
    append_message(session_id,'bot',answer)
    return {'answer':answer}

@app.post('/session')
def new_session():
    return {'session_id':create_session()}

@app.get("/history/{session_id}")
def session_history(session_id: str):
    history = get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return {"history": history}


@app.delete('/session/{session_id}')
def deleteSession(session_id:str):
    delete_session(session_id)
    return {'Status':'cleared'}
    
#class ArticleRequest(BaseModel):
#    rss_url: str = "https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"
#
#@app.post("/fetch-and-store")
#async def fetch_and_store_articles(request: ArticleRequest):
#    try:
#        init_collection()
#
#        print(f"Running fetch from RSS: {request.rss_url}")
#        articles = fetch_articles_from_rss(request.rss_url)
#
#        if not articles:
#            return {"status": "error", "message": "No articles fetched", "data": []}
#
#        print(f"{len(articles)} articles fetched.")
#        
#        embed_and_store_article(articles)
#
#        return {
#            "status": "success",
#            "message": f"{len(articles)} articles fetched and stored.",
#            "data": [{"title": a["title"], "url": a["url"]} for a in articles]
#        }
#
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
 
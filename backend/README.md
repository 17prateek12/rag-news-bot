# 🧠 News-Based Chatbot with RAG & FastAPI

This project is a **news-aware chatbot** using **Retrieval-Augmented Generation (RAG)** powered by FastAPI. It fetches live news from an RSS feed, embeds and stores them in Qdrant, and uses Google Gemini to answer user queries in context. Chat sessions are stored in Redis and optionally persisted to PostgreSQL.

---

## 🚀 Features

- 📰 **RSS-powered**: Fetches and processes the latest news articles
- 🧠 **RAG pipeline**: Uses semantic search + Gemini to generate answers
- 🧵 **Chat sessions**: Persistent with Redis and PostgreSQL
- 🔌 **WebSocket + REST API**: Real-time chat and stateless POST-based querying
- 🌐 **CORS enabled**: Easy integration with frontends

---

## 🧱 Tech Stack

| Component         | Tech/Service                      |
|------------------|------------------------------------|
| Backend API       | FastAPI                           |
| Embedding Model   | Jina Embeddings (`jina-embeddings-v2-base-en`) |
| Vector Store      | Qdrant                            |
| LLM               | Google Gemini 2.0 Flash           |
| Session Storage   | Redis                             |
| Persistent DB     | PostgreSQL                        |
| Article Parsing   | newspaper3k + feedparser          |

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/news-rag-chatbot.git
cd news-rag-chatbot
```

### 2. Create Environment Variables

```
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
JINA_API_KEY=your_jina_api_key
GEMINI_API_KEY=your_google_gemini_api_key
POSTGRES_URL=postgresql://user:password@localhost/dbname
```

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Start the App
```
uvicorn main:app --reload
```

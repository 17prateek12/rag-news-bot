# Context Engine — AI-Powered News Analyst Bot

Context Engine is an advanced AI agentic application designed to go beyond typical headlines. Instead of just displaying news, it uses a multi-source ETL pipeline, local vector indexing, and a **LangGraph-powered Context Agent** to synthesize the background story, chronological timeline of events, and conflicting perspectives.

---

## Key Features

1. **Multi-Source ETL Pipeline**: Ingests articles from multiple RSS feeds and retrieves transcripts from YouTube videos without requiring YouTube API keys.
2. **Transform & Enriched Ingest**: Sanitizes content, detects language, extracts entities (people, orgs, places), and runs Gemini 2.0 Flash classification to automatically tag topics.
3. **Hybrid Ingest Observability**: Logs duration, deduplication stats, extraction successes, and failures in a database. Exposes stats via a dedicated Pipeline Status dashboard.
4. **LangGraph Reasoning Agent**:
   - **Query Rewriter**: Breaks down user queries into multiple search queries.
   - **Similarity Search**: Performs local semantic searches on Qdrant.
   - **Web Search Fallback**: Automatically falls back to Tavily search when local database search coverage is insufficient.
   - **Timeline Generator**: Assembles chronologically ordered milestones.
   - **Synthesizer**: Generates contextual briefs with inline citations.
5. **Personalized Daily Digests**: Generates morning briefs covering topics of interest specified in user watches.
6. **Significant Watch Alerts**: Periodically reviews ingested articles for user-specified keywords and uses Gemini to qualify whether matches represent a significant development before raising notifications.

---

## Tech Stack

- **Backend**: FastAPI, LangGraph, Google GenAI SDK (`text-embedding-004` & `gemini-2.0-flash`), Qdrant Cloud/Local, PostgreSQL (SQLAlchemy), Redis, Celery, `feedparser`, `youtube-transcript-api`.
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Lucide Icons, Zustand, TanStack React Query.

---

## Project Structure

```
contextagent/
├── backend/
│   ├── api/routes/          # HTTP & WebSocket endpoints (auth, chat, digests, watches, pipeline)
│   ├── core/                # DB and Redis setups
│   ├── repositories/        # Vector embedding, Qdrant repository, session stores
│   ├── etl/                 # Extractor, Transformer, Loader pipeline modules
│   ├── agents/              # ContextAgent (LangGraph), DigestAgent, WatchAgent
│   ├── config.py            # Pydantic settings loading
│   ├── main.py              # FastAPI app startup & router mounts
│   ├── models.py            # SQLAlchemy Postgres DB schemas
│   ├── worker.py            # Celery task definitions & schedule definitions
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── src/
    │   ├── components/      # Chat, Layout (Sidebar)
    │   ├── pages/           # ChatPage, DigestPage, WatchesPage, PipelinePage, AuthPage
    │   ├── lib/             # API client, utility functions
    │   ├── hooks/           # useChat (WebSocket manager)
    │   ├── store/           # authStore (Zustand state)
    │   ├── types/           # TS Interfaces
    │   ├── App.tsx          # Router and Query provider setup
    │   ├── main.tsx         # Entry mount
    │   └── index.css        # Tailwind styling
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig.json
    ├── vite.config.ts
    └── package.json
```

---

## Setup & Running Locally

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** & **Redis** running locally or in the cloud.
- **Qdrant** running locally or in the cloud.

### Backend Setup
1. Change directory to `backend`:
   ```bash
   cd backend
   ```
2. Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```
5. In separate terminals, run the Celery worker and beat scheduler:
   ```bash
   celery -A worker.celery_app worker --loglevel=info
   celery -A worker.celery_app beat --loglevel=info
   ```

### Frontend Setup
1. Change directory to `frontend`:
   ```bash
   cd ../frontend
   ```
2. Copy `.env.example` to `.env` and set `VITE_API_URL`:
   ```bash
   cp .env.example .env
   ```
3. Install packages:
   ```bash
   npm install
   ```
4. Run the Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.

# Context Engine — an AI news analyst that reads the news so you can ask it questions

Context Engine is a full-stack application that continuously reads news from RSS feeds, understands what it's reading, and lets you have a real conversation about current events — with every answer grounded in actual articles, not the model's imagination.

Think of it less as "ChatGPT with news" and more as **a research assistant that has already read today's papers and can defend every sentence it writes with a source.**

This README is written so that a backend engineer, a frontend engineer, a product person, and someone who has never touched code can all read it and come away understanding what this project does and how it works. Skip to whichever section answers your question.

---

## Table of contents

1. [What problem this solves](#1-what-problem-this-solves)
2. [What it actually does — in plain English](#2-what-it-actually-does--in-plain-english)
3. [How it works, end to end](#3-how-it-works-end-to-end)
4. [The tech stack, and why each piece was chosen](#4-the-tech-stack-and-why-each-piece-was-chosen)
5. [Architecture diagram](#5-architecture-diagram)
6. [Project structure](#6-project-structure)
7. [Every feature, explained](#7-every-feature-explained)
8. [Running it locally](#8-running-it-locally)
9. [Configuration reference](#9-configuration-reference)
10. [API overview](#10-api-overview)
11. [Design principles this project follows](#11-design-principles-this-project-follows)
12. [Known limitations](#12-known-limitations)
13. [Roadmap / what's next](#13-roadmap--whats-next)

---

## 1. What problem this solves

Ask a general-purpose chatbot "what's happening with X right now" and one of two things happens: it tells you honestly that it doesn't know (its knowledge has a cutoff date), or worse, it *guesses* confidently and gets it wrong.

Context Engine solves this by never answering from memory. Every response is built from a two-step process: **first find real, current articles that are actually relevant, then ask the AI to summarize and explain only what those articles say** — with a citation on every claim. If nothing relevant can be found, it says so, instead of making something up. This pattern is called **RAG — Retrieval-Augmented Generation** — and this project is a complete, working, end-to-end implementation of it, built from scratch rather than assembled from a framework.

## 2. What it actually does — in plain English

- **It reads the news for you, automatically.** A background process checks RSS feeds from real news sources (BBC, Al Jazeera, The Hindu, NDTV, and others) every few hours, pulls in new articles, and files them away — cleaned up, de-duplicated, and indexed so they can be searched instantly.
- **You can chat with it about current events.** Ask "what's going on with the Ukraine ceasefire talks" and it searches everything it has read, picks the most relevant pieces, and writes you a proper answer — citing exactly which articles it used, so you can go read the originals yourself.
- **It remembers the conversation.** Ask a follow-up like "what about the EU's reaction?" and it understands you're still talking about the same topic — it doesn't need you to repeat context.
- **If it doesn't know something, it goes and finds out.** When its own archive doesn't have enough relevant coverage, it automatically does a live web search rather than answering from thin air.
- **It shows you what's trending** — both what's actually big in the news right now, and, separately, what *other users* have been asking about — as two different leaderboards.
- **You can "watch" a topic** (a person, an event, a keyword) and get a daily digest emailed to you automatically summarizing what happened, without having to check back yourself.
- **You can talk to it, literally** — there's voice input, so you can ask a question out loud instead of typing.

## 3. How it works, end to end

There are really two independent halves to this system, running on their own schedules:

### Half one: reading the news (happens continuously, in the background, with no user involved)

1. A scheduled job wakes up and checks every configured RSS feed for new articles.
2. Each new article is cleaned up (HTML stripped, tracking junk removed from URLs) and checked against the database — if it's already been seen, it's skipped.
3. New articles are broken into small, overlapping chunks (so a long article can be searched piece by piece, not just as one giant blob) and each chunk is converted into a numerical representation (an "embedding") that captures its *meaning*, not just its words.
4. Those embeddings are stored in a vector database, ready to be searched by meaning later.
5. The system also scans each article to pull out named things — people, places, organizations — and keeps a running tally of how often each one is mentioned, which is what powers the "trending" feature.

### Half two: answering a question (happens the moment you ask something)

1. Your question is first classified — is this a quick factual lookup ("who is the president of X"), a "why did this happen" question, or a broad "what's the full picture" request? Each type gets handled differently, because they genuinely need different kinds of answers.
2. If you're mid-conversation, your question is rewritten to stand on its own (so "what about him?" becomes something searchable, using context from what you'd been discussing).
3. The system searches its archive **two different ways at once** — once for articles that *mean* something similar to your question, and once for articles that contain the *exact words* you used — and intelligently combines both result sets, because meaning-based and word-based search each catch things the other misses.
4. A second, more careful pass re-scores the top candidates for genuine relevance (this step is slower but much more accurate, so it only runs on a short list, not everything).
5. If local coverage is thin, empty, or too old, it automatically searches the live web to fill the gap.
6. Only *then* does it hand the best evidence to the AI model and ask it to write an answer — with explicit instructions to cite everything and never state something the evidence doesn't support.
7. The final answer is double-checked: any source that isn't actually cited in the text gets dropped from what's shown to you, so you only ever see sources that were genuinely used.

## 4. The tech stack, and why each piece was chosen

No component in this stack was picked by default — each one is solving a specific problem that a simpler choice wouldn't have:

| Layer | Technology | Why this, specifically |
|---|---|---|
| **Backend framework** | FastAPI (Python) | Nearly everything this app does is waiting on something external (a database, a search index, an AI model) — FastAPI's native async support means the server can handle many of these waits *at the same time* instead of one at a time. |
| **Relational database** | PostgreSQL | Stores everything structured: articles, users, chat history, watch lists. Also doubles as the keyword-search engine (via its built-in full-text search) — one fewer service to run. |
| **Vector database** | Qdrant | Purpose-built for "find me things that mean something similar to this," which a normal database isn't designed to do efficiently at scale. |
| **Cache & message broker** | Redis | One piece of infrastructure, four jobs: caching search results so repeat questions are instant, queuing background jobs, rate-limiting login attempts, and broadcasting "new articles just arrived" events in real time. |
| **Background jobs** | Celery | Anything slow (reading RSS feeds, generating daily digests, cleaning up old data) runs here, off to the side, so it never makes a user wait. |
| **AI model** | Google Gemini (via Vertex AI) | One provider handles embeddings, answer generation, *and* voice transcription — fewer integrations, fewer API keys to manage. |
| **Re-ranking model** | A local cross-encoder (`ms-marco-MiniLM-L-6-v2`) | Runs on the server itself rather than calling out to another API — important because this step runs on every single search and needs to be fast. |
| **Named-entity recognition** | spaCy (local) | Same reasoning — this runs on every article and every question, so it needs to be free and instant, not a paid API call. |
| **Live web search fallback** | Tavily | Built specifically for feeding AI systems clean, structured search results — not a general search engine meant for humans to read directly. |
| **Frontend** | React + TypeScript + Vite | A fast, modern, type-safe frontend stack with a quick development loop. |
| **Frontend data-fetching** | React Query (TanStack Query) | Nearly all of this app's frontend state *is* server data (articles, chats, trending) — React Query is built exactly for that, handling caching and refetching without a separate state-management library. |

## 5. Architecture diagram

```
                         ┌───────────────────────┐
   You  ───HTTP / SSE───▶│   React Frontend      │
                         └───────────┬───────────┘
                                     │ REST + streaming, cookie-authenticated
                                     ▼
                         ┌───────────────────────┐
                         │   FastAPI Backend      │◀────────┐
                         └──┬─────────┬───────┬──┘          │
                            │         │       │              │
              SQLAlchemy    │         │       │ REST          │ real-time
                            ▼         │       ▼               │ push
                  ┌──────────────┐    │  ┌──────────────┐     │
                  │  PostgreSQL  │    │  │    Qdrant    │     │
                  │ (data + text │    │  │ (vector      │     │
                  │  search)     │    │  │  search)     │     │
                  └──────────────┘    │  └──────────────┘     │
                                      │                        │
                              Redis (cache, queue, pub/sub) ───┘
                                      │
                                      ▼
                     ┌────────────────────────────┐
                     │  Celery Worker + Scheduler   │──▶ RSS Feeds
                     └────────────────────────────┘
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
          ┌──────────────┐    ┌──────────────┐
          │ Gemini (AI)  │    │   Tavily     │
          │ embeddings + │    │  (live web   │
          │ answers + STT│    │  fallback)   │
          └──────────────┘    └──────────────┘
```

The API server holds no important state of its own — everything that matters lives in Postgres, Qdrant, or Redis — which means you can run several copies of it behind a load balancer with no special coordination needed.

## 6. Project structure

```
context-agent-backend/
├── app/
│   ├── api/routes/       # every HTTP endpoint, grouped by feature (chat, search, admin, ...)
│   ├── core/             # infrastructure: database connections, auth, logging, error handling
│   ├── ingestion/        # the RSS-reading pipeline: fetch → clean → chunk → embed
│   ├── models/           # database table definitions
│   ├── repositories/     # all raw database/Qdrant queries live here, nowhere else
│   ├── schemas/          # request/response shapes (what the API accepts and returns)
│   ├── services/         # the actual business logic — this is where the RAG pipeline lives
│   └── worker/           # background jobs and their schedule
├── alembic/              # database migration history
└── requirements.txt

context-agent-frontend/
├── src/
│   ├── api/              # the one place that talks to the backend
│   ├── components/       # reusable UI pieces, grouped by feature
│   ├── context/           # app-wide state (who's logged in, light/dark theme)
│   ├── hooks/             # reusable data-fetching logic
│   ├── pages/             # one file per screen (Home, Chat, Trending, ...)
│   └── lib/               # small standalone helpers
└── package.json
```

## 7. Every feature, explained

### Reading & indexing the news
- Pulls from multiple RSS sources on a schedule, each with its own parser to handle that source's particular formatting quirks.
- Never stores the same article twice — a database-level rule enforces this, not just application logic.
- Cleans article text, splits it into overlapping chunks (so long articles remain searchable at the paragraph level), and generates a searchable "meaning fingerprint" (embedding) for each chunk.
- Identifies people, places, and organizations mentioned in each article and tracks how often each one comes up, hour by hour.

### Search & conversation
- **Hybrid search**: combines meaning-based search and exact-keyword search, because each one alone misses things the other catches (meaning-search can miss an exact name; keyword-search can miss a differently-worded but relevant article).
- **Re-ranking**: after the first, fast search pass, a second, more careful pass re-scores the top results specifically for relevance — including nudging up very recent articles and down articles that turn out to be about a *former* office-holder or *past* situation, a common source of confusing answers.
- **Live web fallback**: if the archive doesn't have good enough local coverage, it automatically checks the live web instead of answering from a thin or empty result set.
- **Multi-turn memory**: chat sessions persist, follow-up questions are automatically rewritten with context from the conversation so far, and a source cited three messages ago can still be referenced correctly later.
- **Every claim is sourced**: the system is built to refuse to answer rather than make something up when it can't find genuinely relevant evidence.
- **Voice input**: record a question instead of typing it; it's transcribed and handled exactly like a typed message.

### Trending & discovery
- Two separate "trending" lists: what's actually big in the news (based on how often something is mentioned across articles) versus what people are *asking about* (based on real user questions) — genuinely different signals, tracked independently.
- Click into any trending topic to see the specific articles behind it.

### Watches & digests
- Track up to five topics you care about.
- Once a day, a background job checks for new coverage of each watched topic and writes you a summarized digest — and emails you when a new one is ready.

### Accounts & security
- Separate login systems for regular users and administrators, so a compromised user account can never reach admin functionality.
- Sessions are stored in secure, browser-inaccessible cookies rather than anywhere JavaScript could read them — a deliberate defense against a common class of security bug.
- Login attempts are rate-limited to prevent brute-forcing.

### Admin tools
- Manage news sources and categories.
- Trigger a news-ingestion run or a digest run manually, on demand.
- Check the health of the search index and see which categories have no active news source feeding them.

## 8. Running it locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker (for Postgres, Redis, and Qdrant)
- A Google Cloud project with Vertex AI enabled (for embeddings, generation, and speech-to-text)
- A Tavily API key (for the live web-search fallback)

### Step 1 — Start the databases

```bash
cd context-agent-backend
docker-compose up -d
```
This brings up Postgres, Redis, Qdrant, and Adminer (a simple database viewer at whatever port you configure).

### Step 2 — Set up the backend

```bash
cp .env.example .env       # then fill in the values — see the reference table below
pip install -r requirements.txt
python -m spacy download en_core_web_sm
alembic upgrade head       # creates all database tables
```

You'll also need Google Cloud credentials available to the app — the simplest way locally is:
```bash
gcloud auth application-default login
```

Then start three separate processes (each in its own terminal):

```bash
# The API server
python -m uvicorn app.main:app --port 8000 --reload

# The background job runner
celery -A app.worker.celery_app.celery_app worker --loglevel=info -P solo

# The scheduler (triggers jobs like ingestion on a timer)
celery -A app.worker.celery_app.celery_app beat --loglevel=info
```

### Step 3 — Set up the frontend

```bash
cd ../context-agent-frontend
cp .env.example .env       # set VITE_API_URL to wherever your backend is running
npm install
npm run dev
```

Open `http://localhost:5173`. You should see the homepage — but it'll be empty until the first ingestion run happens. You can trigger one manually rather than waiting for the schedule:

```bash
curl -X POST http://localhost:8000/admin/ingest/run \
  -H "X-Admin-Api-Key: <the ADMIN_API_KEY value from your .env>"
```

Give it a minute or two — it's fetching, cleaning, chunking, and embedding real articles — then refresh the homepage.

## 9. Configuration reference

Every setting lives in `context-agent-backend/.env`. Grouped by what they control:

| Group | Variables | What they're for |
|---|---|---|
| **Database** | `DATABASE_URL`, `SYNC_DATABASE_URL` | Postgres connection strings — async for the API, sync for Alembic migrations. |
| **Cache / queue** | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Usually all point at the same Redis instance. |
| **Vector search** | `QDRANT_URL`, `QDRANT_COLLECTION`, `EMBEDDING_DIMENSIONS` | Where the vector database lives and how big each embedding is. |
| **AI models** | `GCP_PROJECT`, `GCP_LOCATION`, `EMBEDDING_MODEL`, `GEMINI_MODEL` | Which Google Cloud project and which models to call. |
| **Chunking** | `CHUNK_SIZE`, `CHUNK_OVERLAP` | How articles are split up before being embedded. |
| **Hybrid search** | `HYBRID_SEMANTIC_LIMIT`, `HYBRID_BM25_LIMIT`, `RRF_K` | How many candidates each search method returns, and how strongly results are re-weighted when combined. |
| **Re-ranking** | `RERANKER_ENABLED`, `RERANKER_MODEL`, `RELEVANCE_SCORE_FLOOR` | Whether the second, careful relevance pass is on, and how strict the cutoff is. |
| **Web fallback** | `WEB_FALLBACK_ENABLED`, `TAVILY_API_KEY`, `WEB_FALLBACK_STALE_HOURS` | Whether/when to check the live web instead of just local coverage. |
| **Caching** | `CACHE_ENABLED`, `CACHE_SEARCH_TTL_SECONDS`, `CACHE_RAG_TTL_SECONDS` | How long different kinds of results are cached before being recomputed. |
| **Auth** | `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_API_KEY` | Session security and the one seeded admin account. |
| **Ingestion** | `ARTICLE_RETENTION_DAYS`, `INGEST_INTERVAL_HOURS` | How long articles are kept, and how often new ones are fetched. |
| **Voice input** | `STT_ENABLED`, `STT_MODEL`, `STT_MAX_AUDIO_BYTES` | Speech-to-text settings and upload limits. |

> **A note on `JWT_SECRET`**: the app will refuse to start if this is left at an obvious placeholder value — don't skip setting it to something real, even for local development.

## 10. API overview

The full backend exposes ~50 endpoints; here are the ones you'll use most:

| What you want to do | Endpoint |
|---|---|
| Search the archive | `GET /search/hybrid?q=...` |
| Ask a one-off question, no login required | `POST /agent/query` |
| Start/continue a logged-in chat | `POST /chat/sessions/{id}/messages` |
| See what's trending | `GET /trending` |
| Register / log in | `POST /auth/register`, `POST /auth/login` |
| Track a topic | `POST /watches` |
| See your digests | `GET /digests` |
| Trigger a news refresh (admin) | `POST /admin/ingest/run` |

Interactive, always-up-to-date documentation for every endpoint is auto-generated by FastAPI and available at `http://localhost:8000/docs` once the server is running.

## 11. Design principles this project follows

- **Never answer without evidence.** If the search pipeline can't find genuinely relevant material, the system says so rather than guessing.
- **Cache aggressively, but invalidate simply.** Every layer of search/answer results is cached, and a single version counter — bumped once whenever new articles arrive — invalidates everything at once, rather than needing to track down every stale cache entry individually.
- **Keep slow work off the request path.** Anything that takes more than a moment (reading RSS feeds, running NLP, sending emails) happens in the background, never while someone is waiting on a response.
- **One clear owner per concern.** Routes handle HTTP, services hold business logic, repositories own the actual database/search queries — each layer has exactly one job, which makes the codebase far easier to navigate and change safely.
- **Fail safe, not silent.** Rate limiting blocks requests if its own backing store is unreachable, rather than quietly letting everything through; errors return structured, consistent responses instead of vague failures.

## 12. Known limitations

Being upfront about the current gaps, rather than glossing over them:

- Real-time "typing" streaming is fully built on the backend but not yet wired into the chat interface — you currently see the full answer appear at once rather than word by word.
- The homepage's quick-search box uses simpler keyword search rather than the full hybrid pipeline the chat experience uses.
- There's no automated test coverage yet for the core search/answer pipeline specifically (other parts of the system are tested).
- A single flaky news source can slow down a full ingestion run — there's no automatic skip-and-retry-later behavior yet.

## 13. Roadmap / what's next

- Wire up real-time streaming responses in the chat UI.
- Add automated tests around the search and answer-generation pipeline.
- Make the news-source list resilient to individual feeds timing out.
- Move the client-side voice-input usage limit to a properly enforced server-side check.
- Explore letting the system make its own decision about *when* to search the live web, rather than following a fixed rule.

---

*Questions, ideas, or found a bug? Open an issue — this project is actively maintained and improving.*
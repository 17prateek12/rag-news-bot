# Context Agent Backend

## Security model

- **`admins` table** — completely separate from future public `users`
- **One admin** — seeded from `ADMIN_EMAIL` / `ADMIN_PASSWORD` on first startup only
- **No admin signup endpoint** — cannot create admins via API
- **Admin JWT** — `token_type: admin_session` (not valid for any future user routes)
- **Cron** — uses `X-Admin-Api-Key` header

## Quick start

```bash
docker compose up -d
# Set ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_API_KEY, JWT_SECRET in .env
uvicorn app.main:app --reload --port 8000
```

Startup automatically: migrations → singleton admin → bootstrap feeds.

## Public (read-only)

| Method | Path |
|--------|------|
| GET | `/health` |
| GET | `/articles` |
| GET | `/articles/{id}` |

## Admin (`/admin/*`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/admin/login` | Admin login |
| GET | `/admin/me` | Current admin |
| GET/POST/DELETE | `/admin/articles` | List / create / delete articles |
| GET/POST/PATCH/DELETE | `/admin/categories` | Category CRUD |
| GET/POST/PATCH/DELETE | `/admin/rss-sources` | RSS feed CRUD |
| POST | `/admin/ingest/run` | Ingest all feeds |
| POST | `/admin/ingest/run/{id}` | Ingest one feed |
| POST | `/admin/maintenance/cleanup` | Delete old articles |
| GET | `/admin/health/feed-coverage` | Category coverage check |

## Admin login

```bash
curl -X POST http://localhost:8000/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@contextagent.local","password":"your-password"}'
```

## Cron ingest

```bash
curl -X POST http://localhost:8000/admin/ingest/run \
  -H "X-Admin-Api-Key: your-admin-api-key"
```

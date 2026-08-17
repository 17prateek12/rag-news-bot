import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def req(method, path, body=None, headers=None, timeout=180):
    url = BASE + path
    data = None
    h = headers or {}
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return {"status": resp.status, "ok": True, "body": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        return {"status": e.code, "ok": False, "body": payload}
    except Exception as e:
        return {"status": None, "ok": False, "body": str(e)}


def main() -> None:
    q = urllib.parse.quote("ukraine war")
    tests = {
        "health": req("GET", "/health", timeout=15),
        "semantic": req("GET", f"/search?q={q}&limit=3"),
        "hybrid": req("GET", f"/search/hybrid?q={q}&limit=3"),
        "agent": req("POST", "/agent/query", {"query": "What is happening in Ukraine?", "limit": 3}),
    }
    login = req(
        "POST",
        "/admin/login",
        {"email": "admin@contextagent.local", "password": "your-strong-password"},
    )
    if login["ok"]:
        auth = {"Authorization": "Bearer " + login["body"]["access_token"]}
        tests["backfill"] = req("POST", "/admin/maintenance/backfill-chunks", headers=auth)
        tests["qdrant"] = req("GET", "/admin/debug/qdrant/status", headers=auth)
        tests["ingest"] = req("POST", "/admin/ingest/run/1", headers=auth, timeout=300)

    for name, res in tests.items():
        ok = res["ok"]
        b = res["body"]
        extra = ""
        if name == "hybrid" and ok:
            extra = f" sem={b.get('semantic_count')} bm25={b.get('bm25_count')} hits={len(b.get('results', []))}"
        elif name == "agent" and ok:
            extra = f" sources={len(b.get('sources', []))} answer={(b.get('answer') or '')[:80]}..."
        elif name == "qdrant" and ok:
            extra = f" points={b.get('points_count')}"
        elif name == "ingest" and ok:
            if b.get("status") == "queued":
                extra = f" status={b.get('status')} task_id={b.get('task_id')[:8]}..."
            else:
                extra = f" embedded={b.get('embedded')} skipped={b.get('embed_skipped')}"
        elif not ok:
            extra = " " + str(b)[:300]
        print(f"{'PASS' if ok else 'FAIL'} {name} ({res['status']}){extra}")


if __name__ == "__main__":
    main()

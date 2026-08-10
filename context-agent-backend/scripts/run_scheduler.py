"""Run Celery worker + beat locally (Windows requires --pool=solo)."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CELERY = ROOT / "sysenv" / "Scripts" / "celery.exe"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Celery worker/beat for Context Agent")
    parser.add_argument(
        "mode",
        choices=["worker", "beat", "worker-beat", "ingest", "cleanup"],
        help="worker: celery worker; beat: scheduler only; worker-beat: both; ingest/cleanup: one-shot task",
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        from app.worker.tasks import ingest_all_feeds

        print(ingest_all_feeds())
        return 0

    if args.mode == "cleanup":
        from app.worker.tasks import cleanup_old_articles

        print(cleanup_old_articles())
        return 0

    cmd = [str(CELERY), "-A", "app.worker.celery_app"]
    if args.mode in {"worker", "worker-beat"}:
        cmd.extend(["worker", "--loglevel=info", "--pool=solo"])
        if args.mode == "worker-beat":
            cmd.append("-B")
    else:
        cmd.extend(["beat", "--loglevel=info"])

    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())

"""RQ-Worker-Entrypoint (nur nötig, wenn USE_QUEUE=true).

Start:  python worker.py
"""

from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

from txtsong.config import get_settings


def main() -> None:
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(connection=conn)], connection=conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

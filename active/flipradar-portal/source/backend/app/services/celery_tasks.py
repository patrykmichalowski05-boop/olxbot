"""Optional Celery worker for the development backend."""

import os

from celery import Celery


app = Celery(
    "flip_hunter_backend",
    broker=os.getenv(
        "FLIP_BACKEND_REDIS_URL",
        "redis://127.0.0.1:6379/2",
    ),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "poll-dev-outbox": {
            "task": "flip_hunter.outbox.poll",
            "schedule": 60.0,
        },
    },
)


@app.task(name="flip_hunter.outbox.poll")
def poll_outbox():
    from backend.app.core.settings import Settings

    from backend.app.db.session import (
        make_session_factory,
    )

    from backend.app.services.outbox_dispatch import (
        process_batch,
    )

    engine, factory = make_session_factory(
        Settings().database_url
    )

    try:
        return process_batch(
            factory,
            limit=20,
        )

    finally:
        engine.dispose()

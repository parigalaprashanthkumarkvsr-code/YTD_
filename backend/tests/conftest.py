import os
import tempfile

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["DOWNLOAD_DIR"] = tempfile.mkdtemp(prefix="ytd-tests-")
os.environ["MAX_CONCURRENT_JOBS"] = "2"
os.environ["CLEANUP_INTERVAL_SECONDS"] = "3600"

import httpx
import pytest
from app.main import app
from app.services.job_manager import manager


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
async def clean_jobs():
    yield
    for job_id in list(manager._jobs):
        job = manager.get(job_id)
        if job is not None:
            job.cancel_event.set()
            if job.task is not None and not job.task.done():
                job.task.cancel()
        await manager.cancel(job_id)

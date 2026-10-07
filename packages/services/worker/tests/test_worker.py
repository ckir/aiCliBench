import asyncio

from ai_runtime import FakeChatModel
from ai_service_worker import WorkerConfig, health_check, run_job


def test_worker_imports():
    import ai_service_worker

    assert ai_service_worker is not None


def test_worker_health():
    assert health_check()["status"] == "ok"


def test_worker_runs_job():
    async def _run() -> None:
        model = FakeChatModel(responses=[FakeChatModel.text("done")])
        answer = await run_job(model, "hi", config=WorkerConfig())
        assert answer == "done"

    asyncio.run(_run())

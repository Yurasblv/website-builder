import asyncio
import pickle
import time
from typing import Any

from celery import Task
from loguru import logger

from app.celery import celery_app
from app.enums import PBNGenerationStatus
from app.schemas.pbn import PBNDeploy
from app.services.generation.pbn import PBNDeployService


@celery_app.task(
    name="pbn_redeploy_task", bind=True, autoretry_for=(Exception,), retry_jitter=False, retry_backoff=30, max_retries=1
)
def pbn_redeploy_task(task: Task, data: bytes) -> None:
    time.sleep(3)  # wait for task registration TODO: user celery.signals.task_prerun

    pbn: PBNDeploy = pickle.loads(data)

    async def _run() -> None:
        instance = await PBNDeployService._init()
        await instance._set_params(pbn)
        await instance.run()
        logger.success(f"PBN {instance.obj.id} was successfully deployed and built.")

    try:
        with asyncio.Runner() as runner:
            runner.run(_run())

    except Exception as e:
        if task.request.retries >= task.max_retries:
            with asyncio.Runner() as runner:
                status_to_set = PBNGenerationStatus.ERROR

                runner.run(PBNDeployService.finalize(pbn_id=str(pbn.id), status_to_set=status_to_set))
                logger.exception(f"PBN {pbn.id} was retry failed. Status: {status_to_set}")

        raise e


@celery_app.task
def pbn_run_failure_redeploy_task() -> None:
    async def _run() -> None:
        instance = await PBNDeployService._init()
        generate_list = await instance.prepare()

        for pbn in generate_list:
            pbn_redeploy_task.apply_async(kwargs=dict(data=pickle.dumps(pbn)))

    with asyncio.Runner() as runner:
        runner.run(_run())


@celery_app.task
def pbn_finalize_redeploy_task(*_: Any, **kwargs: Any) -> None:
    with asyncio.Runner() as runner:
        runner.run(PBNDeployService.finalize(**kwargs))

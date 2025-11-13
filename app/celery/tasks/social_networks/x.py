import asyncio

from app.celery import celery_app


@celery_app.task
def create_post_x_task() -> None:
    from app.services.authors.social_networks.x import SocialNetworkXService

    with asyncio.Runner() as runner:
        runner.run(SocialNetworkXService().generate_post())

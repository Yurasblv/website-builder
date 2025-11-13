import asyncio
import random

import tweepy
from loguru import logger
from sentry_sdk import capture_exception

from app.enums import SocialNetworkType
from app.models import SocialNetworkX
from app.schemas import PostCreate, Tweet
from app.services.ai import TweetGenerationService
from app.utils import UnitOfWorkNoPool


class SocialNetworkXService:
    def __init__(self) -> None:
        self.tweet_service = TweetGenerationService()
        self.min_delay = 1
        self.max_delay = 5

    async def make_time_gap(self) -> None:
        """
        Make a time gap between posts, so that they don't get posted at the same time

        """

        delay_minutes = random.randint(self.min_delay, self.max_delay)
        logger.info(f"Waiting {delay_minutes} minutes before posting")

        await asyncio.sleep(delay_minutes * 60)

    async def generate_post(self) -> None:
        """Generate post for social type"""

        # TODO: Refactor this to use the `join_load_list`

        async with UnitOfWorkNoPool() as uow:
            db_authors = await uow.author.get_authors_by_social_network(
                created_by_id=None, social_network_type=SocialNetworkType.X
            )

        for author, social_network in db_authors:
            await self.make_time_gap()

            try:
                async with UnitOfWorkNoPool() as uow:
                    recent_posts_x = await uow.post_x.get_multi(social_network_id=social_network.id)

                thread_post = await self.tweet_service.generate_tweet(
                    introduction=author.introduction, forbidden_topics=recent_posts_x
                )

                post = await self.publish_post(thread_post=thread_post, social_network=social_network)

                if not post:
                    continue

                async with UnitOfWorkNoPool() as uow:
                    await uow.post_x.create(post)

            except Exception as e:
                logger.error(f"Error making thread post for author {author.id}: {e}")

    @staticmethod
    async def publish_post(thread_post: Tweet, social_network: SocialNetworkX) -> PostCreate | None:
        """
        Publish thread post on X(Twitter)

        Args:
            thread_post: thread post to publish
            social_network: SocialNetworkX object

        Returns:
            Created post object or None if failed
        """

        try:
            client = tweepy.Client(
                consumer_key=social_network.api_key,
                consumer_secret=social_network.api_secret,
                access_token=social_network.access_token,
                access_token_secret=social_network.access_token_secret,
            )

            client.session.proxies = {}  # proxy
            response = client.create_tweet(text=thread_post.text, user_auth=True)
            logger.info(f"X response: {response}")

            if response.errors:
                logger.error(f"Error posting X thread post: {response.errors}")
                return None

            return PostCreate(
                social_network_id=social_network.id,
                text=thread_post.topic,
                post_type=social_network.social_network_type,
            )

        except Exception as e:
            capture_exception(e)
            logger.warning(f"Error posting X thread post: {e}")

            return None

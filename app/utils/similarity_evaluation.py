from openai import AsyncClient
from scipy.spatial.distance import cosine

from app.core.config import settings


class SimilarityEvaluator:
    def __init__(self) -> None:
        self.client = AsyncClient(api_key=settings.ai.OPENAI_API_KEY)
        self.storage: dict[str, list[float]] = dict()

    async def close(self) -> None:
        await self.client.close()

    @staticmethod
    def cosine_similarity(x: list[float], y: list[float]) -> float:
        return 1 - cosine(x, y)

    @staticmethod
    def jaccard_similarity(topic1: str, topic2: str) -> float:
        label1 = set(topic1.lower().split())
        label2 = set(topic2.lower().split())
        return 1.0 - ((len(label1.union(label2)) - len(label1.intersection(label2))) / len(label1.union(label2)))

    async def get_embedding(self, text: str, model: str = "text-embedding-3-large") -> list[float]:
        text = text.replace("\n", " ")

        if text in self.storage:
            return self.storage[text]

        result = await self.client.embeddings.create(input=[text], model=model)
        embedding = result.data[0].embedding
        self.storage[text] = embedding

        return embedding

    async def _check_similarity(self, topic_1: str, topic_2: str, similarity_point: float) -> bool:
        topic_1_emb = await self.get_embedding(topic_1)
        topic_2_emb = await self.get_embedding(topic_2)

        cosine_similarity = self.cosine_similarity(topic_1_emb, topic_2_emb)
        jaccard_similarity = self.jaccard_similarity(topic_1, topic_2)

        similarity = 0.7 * cosine_similarity + 0.3 * jaccard_similarity
        return similarity > similarity_point

    async def is_similar(self, topic: str, layer: int = 1) -> bool:
        similarity_point = settings.ai.get_similar_point(layer)

        if not self.storage:
            await self.get_embedding(topic)
            return False

        existed_topics = list(self.storage.keys()).copy()

        for existed_topic in existed_topics:
            if await self._check_similarity(topic, existed_topic, similarity_point):
                return True

        return False

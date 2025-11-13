import requests
from aiohttp import ClientSession

from app.core import settings


class ImageGenerator:
    def __init__(self) -> None:
        self.headers = {"x-freepik-api-key": settings.ai.FREEPIK_API_KEY}
        self.query_count: dict = {}
        self.used_urls: set = set()

    @staticmethod
    def prepare_payload(
        image_query: str,
        orientation: str = None,
        page: int = 10,
        limit: int = 10,
        order: str = "relevance",
        large_image: bool = False,
    ) -> dict:
        querystring = {
            "page": page,
            "limit": limit,
            "order": order,
            "term": image_query,
            "filters[content_type][photo]": "1",
            "filters[ai-generated][excluded]": "1",
            "filters[license][premium]": "1",
        }

        if orientation:
            querystring[f"filters[orientation][{orientation}]"] = "1"

        if large_image:
            querystring["filters[color]"] = "white"
            querystring["term"] = f"{querystring['term']} (in white color)"

        return querystring

    async def retrieve_image_from_stock(
        self,
        session: ClientSession,
        image_query: str,
        orientation: str = None,
        large_image: bool = False,
        page: int = 10,
        limit: int = 10,
        order: str = "relevance",
    ) -> str:
        self.query_count[image_query] = self.query_count.get(image_query, -1) + 1
        current_count = self.query_count[image_query]
        filter_words = ["illustration", "female", "male", "cartoon", "character"]

        querystring = self.prepare_payload(
            image_query=image_query,
            orientation=orientation,
            page=page,
            limit=limit,
            order=order,
            large_image=large_image,
        )
        async with session.get(settings.ai.FREEPIK_URL, headers=self.headers, params=querystring) as response:
            response_data = await response.json()
            response.raise_for_status()

        result_dict = response_data.get("data", [])

        if "man" in image_query.split():
            filter_words.extend(["woman", "lady", "girl", "businesswoman", "businesslady"])
        if "woman" in image_query.split():
            filter_words.extend(["boy", "businessman"])

        filtered_urls = [
            image
            for image in result_dict
            if not any(word in image["image"]["source"]["url"] for word in filter_words)
            and image["image"]["source"]["url"] not in self.used_urls  # Check if URL was already used
        ]

        if not filtered_urls:
            self.used_urls.clear()

            filtered_urls = [
                image
                for image in result_dict
                if not any(word in image["image"]["source"]["url"] for word in filter_words)
            ]

        if current_count >= len(filtered_urls):
            current_count = 0

        image_dict = filtered_urls[current_count]
        image_url = image_dict["image"]["source"]["url"]
        self.used_urls.add(image_url)

        if not large_image:
            return image_url

        image_id = image_dict["id"]
        download_url = f"https://api.freepik.com/v1/resources/{image_id}/download"
        download_querystring = {"image_size": "medium"}
        response = requests.request("GET", download_url, headers=self.headers, params=download_querystring)
        return response.json()["data"]["url"]

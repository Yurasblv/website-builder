import json
import re

from pydantic import UUID4

from app.enums.open_ai import banwords
from app.models import PageCluster
from app.services.storages import ovh_service
from app.utils.unitofwork import UnitOfWork


def extract_text_from_content(item: dict) -> list[str]:
    """
    Recursively extract text from content field and its nested structures.

    Args:
        item: The item to extract text from.

    Returns:
        A list of extracted texts.
    """

    texts = []

    content = item.get("content", None)

    if content:
        texts.append(content)

    for child in item.get("children", []):
        texts.extend(extract_text_from_content(child))

    return texts


def process_ban_words(data: list[dict], ban_words: list[str]) -> list[str]:
    """
    Check for banned words in the text and return a list of found words.

    Args:
        data: The data to check for banned words.
        ban_words: The list of banned words to check against.

    Returns:
        A list of banned words found in the data.
    """

    all_texts = []
    ban_words_mapping = {word.lower(): word for word in ban_words}
    pattern = r"\b(?:" + "|".join(re.escape(word.lower()) for word in ban_words) + r")\b"
    regex = re.compile(pattern, re.IGNORECASE)

    for item in data:
        all_texts.extend(extract_text_from_content(item))

    return list({ban_words_mapping[match] for text in all_texts for match in regex.findall(text.lower())})


async def check_ban_words(page_id: UUID4) -> list[str]:
    """
    Check for banned words in a page.

    Args:
        page_id: The ID of the page to check.

    Returns:
        A list of banned words found in the page.
    """

    async with UnitOfWork() as uow:
        page: PageCluster = await uow.page_cluster.get_one(id=page_id, join_load_list=[uow.page_cluster.cluster_load])

        release = page.current_release

        if not release:
            return []

    file = await ovh_service.get_file_by_name(release)

    if not file:
        return []

    ban_words: dict[str, str] = getattr(banwords, f"REPLACEMENTS_{page.cluster.language.name}")

    return process_ban_words(json.loads(file), ban_words=list(ban_words.keys()))

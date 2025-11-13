import json
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.schemas.elements import ElementContent


class PageServiceBase:
    @staticmethod
    def jsonify_page_data(data: list[dict[str, Any]] | list[ElementContent]) -> bytes:
        """
        Convert page content data to json and encode it to bytes.

        Args:
            data: list of elements with generated data
        Returns:
            json data in bytes
        """
        if data and isinstance(data, list) and isinstance(data[0], ElementContent):
            data = [content.model_dump(warnings=False) for content in data]  # type:ignore
        return json.dumps(jsonable_encoder(data)).encode("utf-8")

    @staticmethod
    def bleach_clean_data(content: list[ElementContent]) -> list[ElementContent]:
        """
        Cleaning incoming updated content for page with bleach tool (https://bleach.readthedocs.io/).
        Uses in case when customer set up styles and reordering right after generation.
        Especially necessary for H2 tags due to html format of content to prevent script injection.
        Look settings for a list of tags which are allowed to be in content.
        Tags which are not in setting will be converted to default string.

        Args:
            content: array of elements with generated data and formatted by FE

        Returns:
            incoming content filtered with bleach cleaner
        """
        # TODO: find solution for avoid replacing symbols (e.g & replaces with &amp;)

        # for element in content:
        #     if element.content:
        #         element.content = bleach_cleaner(
        #             element.content, tags=settings.ai.ALLOWED_TAGS, attributes=settings.ai.ALLOWED_ATTRIBUTES
        #         )
        return content

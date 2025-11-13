from app.enums import StructurePrompts
from app.schemas import ListElementOutput
from app.services.ai.ai import AIBase


class DomainAIService:
    @classmethod
    async def generate_ai_domains(cls, keyword: str, category: str) -> ListElementOutput:
        """
        Generate AI domains based on a keyword and category.

        Args:
            keyword: The keyword to use for generating domains.
            category: The category of the domain.

        Returns:
            List of generated domain names.
        """

        return await AIBase().gpt_request(
            prompt=StructurePrompts.DOMAIN_NAMES_GENERATION_TEMPLATE,
            output_schema=ListElementOutput,
            keyword=keyword,
            category=category,
        )

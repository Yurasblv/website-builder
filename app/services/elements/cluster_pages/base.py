import ast
import re
from functools import partial
from typing import Any

from loguru import logger
from pydantic import BaseModel
from urllib3.util import parse_url

from app.core.config import settings
from app.enums import (
    Country,
    ElementPrompts,
    FormattingPrompts,
    HumanizationPrompts,
    ImagePrompts,
    InformationalTagType,
    IntentPrompts,
    Language,
    ObjectExtension,
    OpenAIPromptType,
)
from app.models import Author
from app.schemas import AuthorElementContent, ElementStyleParam, H2ContentInput, H2ContentOutput
from app.schemas.elements import (
    ElementContent,
    ElementSettings,
    FactsOutputSchema,
    FAQOutputSchema,
    GraphOutputSchema,
    HeadersListSchema,
    ImageAnnotationOutputSchema,
    ListElementOutput,
    QuizOutputSchema,
    StringElementOutput,
    TableOutputSchema,
)
from app.schemas.elements.cluster_pages.base import CaseCheck, H2HeaderSchema, PageMetadataSchema
from app.schemas.page.cluster_page import ClusterPageGenerationMetadata
from app.services.ai import AIBase, ChainBuilder
from app.services.ai.image_processing import ImageProcessor
from app.services.storages import ovh_service
from app.utils.banwords import remove_banwords
from app.utils.convertors import check_lowercase, remove_links, remove_quotes, strip_braces
from app.utils.decorators import retry_element_processing, traceable_generate


class ElementServiceBase:
    def __init__(
        self,
        user_email: str,
        language: Language,
        target_country: Country,
        page_metadata: ClusterPageGenerationMetadata,
        cluster_keyword: str,
        generation_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.user_email = user_email
        self.language = language
        self.target_country = target_country
        self.page_metadata = page_metadata
        self.cluster_keyword = cluster_keyword
        self.generation_key = generation_key
        self.chain_builder = ChainBuilder()
        self.ai: AIBase = None
        self.image_processor = ImageProcessor(
            country=getattr(self.page_metadata.geolocation, "country", None),
            city=getattr(self.page_metadata.geolocation, "city", None),
        )

    async def __aenter__(self) -> "ElementServiceBase":
        self.ai = await AIBase().__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            await self.ai.__aexit__(None, None, tb)
            await self.chain_builder.close()

        except Exception:
            return None

    async def page_content_post_process(self, *args: Any, **kwargs: Any) -> list[ElementContent]:
        raise NotImplementedError

    @staticmethod
    def create_custom_author_element(
        custom_author: Author | AuthorElementContent, params: ElementStyleParam
    ) -> ElementContent:
        """
        Create an author element

        Args:
            custom_author: db Author record to create
            params: parameters

        Returns:
            mapper with a key as element name and value as ElementContent schema
        """
        ec = partial(ElementContent, position=params.position, processed=True, style=params.style)

        avatar_div_container = ec(tag="AUTHOR", href=custom_author.website_link)
        if custom_author.avatar:
            avatar_div_container.children.append(
                ec(
                    tag="IMG",
                    href=custom_author.avatar_url,
                    args=ElementSettings(image_alt_tag=f"Author {custom_author.full_name}"),
                )
            )

        for tag, content in custom_author.extra_info:
            if content:
                avatar_div_container.children.append(ec(tag=tag, content=content))

        return avatar_div_container

    async def generate_title(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        element_content.content = self.page_metadata.topic_name
        element_content.processed = True
        return element_content

    @traceable_generate(
        tags=["META_WORDS"],
    )
    async def generate_meta_words(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        response = await self.ai.instructor_request(
            prompt=ElementPrompts.META_WORDS_GENERATION_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
            ),
            assistant=ElementPrompts.META_WORDS_GENERATION_ASSISTANT,
            output_schema=ListElementOutput,
        )

        if response:
            element_content.content = response.model_dump_json(warnings=False)
            element_content.processed = True
        return element_content

    @traceable_generate(
        tags=["META_DESCRIPTION"],
    )
    async def generate_meta_description(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        response: StringElementOutput = await self.ai.instructor_request(
            prompt=ElementPrompts.META_DESCRIPTION_GENERATION_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                keyword=self.cluster_keyword,
            ),
            assistant=ElementPrompts.META_DESCRIPTION_GENERATION_ASSISTANT,
            output_schema=StringElementOutput,
        )

        if response:
            element_content.content = response.get_normalized(language=self.language)
            element_content.processed = True

        return element_content

    @traceable_generate(
        tags=["H1"],
    )
    async def generate_h1_header(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        response: StringElementOutput = await self.ai.instructor_request(
            prompt=ElementPrompts.H1_GENERATION_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                keyword=self.cluster_keyword,
                country=self.target_country,
            ),
            assistant=ElementPrompts.H1_GENERATION_ASSISTANT,
            output_schema=StringElementOutput,
        )

        title = await self.ai.replace_string_camel_case(input_string=response.data, language=self.language)

        element_content.content = title.get_normalized(language=self.language)
        element_content.processed = True

        return element_content

    @traceable_generate(
        tags=["PAGE_METADATA"],
    )
    async def regenerate_page_metadata(self, text: str) -> BaseModel:
        assistant = getattr(ElementPrompts, f"PAGE_METADATA_ASSISTANT_{self.language.name}")
        prompt = ElementPrompts.PAGE_METADATA_PROMPT.format(
            content=text,
            language=self.language,
            country=self.target_country,
            search_intent=self.page_metadata.search_intent,
            keyword=self.cluster_keyword,
            topic=self.page_metadata.topic_name,
        )

        updated_metadata = await self.ai.instructor_request(
            prompt=prompt,
            output_schema=PageMetadataSchema,
            assistant=assistant,
            system="You are an expert SEO content strategist.",
        )

        formatted_metadata: PageMetadataSchema = await self.ai.replace_json_camel_case(
            input_text_object=updated_metadata,
            output_schema=PageMetadataSchema,
            language=self.language,
            explanation="",
        )

        return formatted_metadata.remove_metadata_banwords(language=self.language)

    @traceable_generate(
        tags=["HEAD_CONTENT"],
    )
    async def create_head_content_tag(self, element_content: ElementContent) -> ElementContent:
        logger.info(f"Page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        element_content.children.extend(
            await self.create_p_tags(position=element_content.position, prompt_for=ElementPrompts.H1_CONTENT_TEMPLATE)
        )
        element_content.processed = bool(element_content.children)

        return element_content

    @traceable_generate(
        tags=["IMG"],
    )
    async def create_image_content(self, element_content: ElementContent, summary: str) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")

        annotation: ImageAnnotationOutputSchema = await self.ai.instructor_request(
            prompt=ImagePrompts.IMAGE_GENERATION_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                keyword=self.cluster_keyword,
                language=self.language,
                summary=summary,
            ),
            assistant=ImagePrompts.IMAGE_GENERATION_ASSISTANT,
            output_schema=ImageAnnotationOutputSchema,
            system="You are a helpful assistant for image generation.",
        )

        if not annotation:  # check if prompt for image creation was generated
            return element_content

        annotation = annotation.remove_banwords_annotation(language=self.language)

        image_bytes: bytes = b""

        img_providers = [("Open AI", self.ai.generate_image), ("FLUX", self.ai.generate_image_with_flux)]

        for provider_name, func in img_providers:
            try:
                image_bytes = await func(prompt=annotation.prompt)
                break

            except Exception as e:
                logger.exception(
                    f"Error generating image with {provider_name} for {self.page_metadata.topic_name}: {e}"
                )

        if not image_bytes:
            return element_content

        image_with_metadata = await self.image_processor.process_image(
            image_bytes=image_bytes,
        )

        ovh_img_filename = await ovh_service.save_file(
            data=image_with_metadata,
            object_name=ovh_service.construct_object_name(
                user_email=self.user_email,
                cluster_id=self.page_metadata.cluster_id,
                page_id=self.page_metadata.page_uuid,
                content_id=element_content.content_id,
                extension=ObjectExtension.WEBP,
            ),
        )

        element_content.href = parse_url(f"{ovh_service.settings.topics_uri}/{ovh_img_filename}").url
        element_content.processed = True
        element_content.settings = ElementSettings(image_alt_tag=annotation.image_annotation)

        element_content.children.append(
            ElementContent(
                tag=InformationalTagType.FIGCAPTION,
                content=annotation.image_annotation,
                position=element_content.position,
                processed=True,
            )
        )

        return element_content

    async def create_p_tags(self, position: int, prompt_for: OpenAIPromptType | str = "") -> list[ElementContent]:
        p_tags_elements: list[ElementContent] = []
        prompt = ElementPrompts.HEAD_CONTENT_GENERATOR_TEMPLATE + prompt_for
        ec = partial(
            ElementContent,
            tag=InformationalTagType.P,
            position=position,
            processed=True,
            html=True,
        )

        response: StringElementOutput = await self.ai.gpt_request(
            prompt=prompt.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                keywords=self.page_metadata.keywords,
                language=self.language,
                country=self.target_country,
                intent=self.page_metadata.search_intent,
            ),
            output_schema=StringElementOutput,
        )

        humanization_prompt = HumanizationPrompts.for_lang(language=self.language)

        humanized_content: StringElementOutput = await self.ai.instructor_request(
            prompt=humanization_prompt.format(
                content=response.data,
                language=self.language,
            ),
            output_schema=StringElementOutput,
        )

        formatted_response: str = humanized_content.get_normalized(language=self.language)

        p_tags: ListElementOutput = await self.ai.instructor_request(
            prompt=ElementPrompts.P_TAG_CHUNKING_TEMPLATE.format(
                text=formatted_response,
            ),
            output_schema=ListElementOutput,
        )

        p_tags = self.remove_double_quotes(p_tags.data)

        return p_tags_elements + [ec(content=content) for content in p_tags]

    @staticmethod
    def clean_text(text: str) -> str:
        match = re.match(r"^<p>(.*)</p>$", text, re.DOTALL)

        return f"<p>{remove_quotes(match.group(1))}</p>" if match else text

    @staticmethod
    def extract_content_value(generated_text: str) -> str:
        match = re.search(r'content="(.*?)"', generated_text)
        return match.group(1) if match else generated_text

    def remove_double_quotes(self, texts: list[str]) -> list[str]:
        return [self.clean_text(text) for text in texts]

    @staticmethod
    def check_lowercase_headers(headers_schema: HeadersListSchema) -> str:
        short_all_lower = all(check_lowercase(h.short) for h in headers_schema.headers)
        long_all_lower = all(check_lowercase(h.long) for h in headers_schema.headers)

        match short_all_lower, long_all_lower:
            case True, True:
                return settings.ai.LOWERCASE_WARNING

            case True, False:
                return "All short headers start with a lowercase letter. Fix capitalization for short headers only."

            case False, True:
                return "All long headers start with a lowercase letter. Fix capitalization for long headers only."

            case _:
                return ""

    @staticmethod
    def clean_response(response_text: str) -> str:
        if "[" in response_text:
            response_text = response_text[response_text.find("[") :]

        if "]" in response_text:
            response_text = response_text[: response_text.rfind("]") + 1]

        response_text = re.sub(r"```python|```json|```|\n```", "", response_text)

        response_text = response_text.strip()

        return response_text

    @retry_element_processing
    @traceable_generate(
        tags=["NEWS_BUBBLE"],
    )
    async def create_news_bubble(
        self,
        element_content: ElementContent,
    ) -> ElementContent:
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")

        response = await self.ai.gpt_request(
            prompt=ElementPrompts.NEWS_BUBBLE_TEMPLATE.format(
                keyword=self.cluster_keyword,
                topic=self.page_metadata.topic_name,
                keywords=self.page_metadata.keywords,
                intent=self.page_metadata.search_intent,
                language=self.language,
                country=self.target_country,
            ),
            output_schema=StringElementOutput,
        )

        humanization_prompt = HumanizationPrompts.for_lang(language=self.language)
        humanized_content: StringElementOutput = await self.ai.instructor_request(
            prompt=humanization_prompt.format(
                content=response.data,
                language=self.language,
            ),
            output_schema=StringElementOutput,
        )

        formatted_response: str = humanized_content.get_normalized(language=self.language)

        news_bubble: StringElementOutput = await self.ai.replace_string_camel_case(
            input_string=formatted_response, language=self.language
        )

        if news_bubble:
            element_content.children.append(
                ElementContent(
                    tag=InformationalTagType.P,
                    position=element_content.position,
                    content=news_bubble.data,
                    processed=True,
                    html=True,
                )
            )

        if element_content.children:
            element_content.processed = True

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["GRAPH"],
    )
    async def create_graph(self, element_content: ElementContent) -> ElementContent:
        """
        Creates graph in html format by incoming theme in topic.

        Args:
            element_content: ElementContent object.

        Returns:
            An object representing the Graph block.
        """
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")

        prompt = ElementPrompts.GRAPH_GENERATOR_TEMPLATE
        if self.page_metadata.target_audience:
            prompt += getattr(ElementPrompts, f"TARGET_AUDIENCE_EXTENSION_{self.language.name}").format(
                target_audience=self.page_metadata.target_audience
            )

        response: GraphOutputSchema = await self.ai.instructor_request(
            prompt=prompt.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                keyword=self.cluster_keyword,
            ),
            assistant=ElementPrompts.GRAPH_GENERATOR_ASSISTANT,
            output_schema=GraphOutputSchema,
        )
        if not response:
            return element_content

        title = await self.ai.replace_string_camel_case(input_string=response.label, language=self.language)

        response.label = title.data or response.label
        response = response.get_normalized(language=self.language)
        output = response.transform_to_element()

        element_content.content = output.model_dump_json(warnings=False)
        element_content.processed = bool(element_content.content)

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["QUIZ"],
    )
    async def create_quiz(self, element_content: ElementContent) -> ElementContent:
        """
        Creates quiz in html format by incoming theme in topic.

        Args:
            element_content: ElementContent object.

        Returns:
            An object representing the Quiz block.
        """
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        response: QuizOutputSchema = await self.ai.instructor_request(
            prompt=ElementPrompts.QUIZ_GENERATOR_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                keyword=self.cluster_keyword,
            ),
            assistant=ElementPrompts.QUIZ_GENERATOR_ASSISTANT,
            output_schema=QuizOutputSchema,
        )

        if not response:
            return element_content

        title = await self.ai.replace_string_camel_case(input_string=response.title, language=self.language)

        response.title = title.data or response.title
        response = response.get_normalized(language=self.language)

        element_content.content = response.model_dump_json(warnings=False)
        element_content.processed = bool(element_content.content)

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["TABLE"],
    )
    async def create_table(self, element_content: ElementContent) -> ElementContent:
        """
        Creates table in html format by incoming theme in topic.

        Args:
            element_content: ElementContent object.

        Returns:
            An object representing the Table block.
        """
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")

        prompt = ElementPrompts.TABLE_GENERATOR_TEMPLATE
        if self.page_metadata.target_audience:
            prompt += getattr(ElementPrompts, f"TARGET_AUDIENCE_EXTENSION_{self.language.name}").format(
                target_audience=self.page_metadata.target_audience
            )

        response: TableOutputSchema = await self.ai.instructor_request(
            prompt=prompt.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                keyword=self.cluster_keyword,
            ),
            output_schema=TableOutputSchema,
        )

        if not response:
            return element_content

        title = await self.ai.replace_string_camel_case(input_string=response.title, language=self.language)
        response.title = title.data or response.title
        response = response.get_normalized(language=self.language)

        element_content.content = response.model_dump_json(warnings=False)
        element_content.processed = bool(element_content.content)

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["FAQ"],
    )
    async def create_faqs(self, element_content: ElementContent) -> ElementContent:
        """
        Creates faq div container containing questions and answers depending on topic as main theme.

        Args:
            element_content: ElementContent object.

        Returns:
            An object representing the FAQ block.
        """
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")

        response: FAQOutputSchema = await self.ai.instructor_request(
            prompt=ElementPrompts.FAQ_GENERATOR_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                keyword=self.cluster_keyword,
            ),
            output_schema=FAQOutputSchema,
        )

        if not response:
            return element_content

        title = await self.ai.replace_string_camel_case(input_string=response.title, language=self.language)
        response.title = title.data or response.title
        response = response.get_normalized(language=self.language)

        element_content.content = response.model_dump_json()
        element_content.processed = bool(element_content.content)

        return element_content

    @retry_element_processing
    @traceable_generate(
        tags=["FACTS"],
    )
    async def create_facts(self, element_content: ElementContent) -> ElementContent:
        """
        Creates facts div container containing header,
            description and list of timelines depending on topic as main theme.

        Args:
            element_content: ElementContent object.

        Returns:
            An object representing the facts block.
        """
        logger.info(f"Cluster page {self.page_metadata.topic_name} creating element = {element_content.tag}")
        response: FactsOutputSchema = await self.ai.instructor_request(
            prompt=ElementPrompts.FACTS_CREATION_TEMPLATE.format(
                topic=self.page_metadata.topic_name,
                language=self.language,
                country=self.target_country,
                n=4,
                keyword=self.cluster_keyword,
            ),
            output_schema=FactsOutputSchema,
        )

        if not response:
            return element_content

        content: FactsOutputSchema = await self.ai.replace_json_camel_case(
            input_text_object=response,
            output_schema=FactsOutputSchema,
            language=self.language,
            explanation="",
        )

        content = content.get_normalized(language=self.language)

        element_content.content = content.model_dump_json()
        element_content.processed = bool(element_content.content)

        return element_content

    async def create_h2_headers(self, content: list[str], h2_tags_number: int) -> list[H2HeaderSchema]:
        """
        Generates H2 tags for a given topic by amount.

        Returns:
            list with h2 titles according to number of h2_tags_number
        """
        response: HeadersListSchema = await self.ai.gpt_request(
            prompt=ElementPrompts.H2_HEADERS_GENERATION_TEMPLATE,
            assistant=ElementPrompts.H2_HEADERS_GENERATION_ASSISTANT,
            output_schema=HeadersListSchema,
            keyword=self.cluster_keyword,
            country=self.target_country,
            language=self.language,
            h2_tags_number=h2_tags_number,
            content=content,
            topic=self.page_metadata.topic_name,
        )

        if explanation := self.check_lowercase_headers(response):
            fixed: HeadersListSchema = await self.ai.replace_json_camel_case(
                input_text_object=response,
                output_schema=HeadersListSchema,
                language=self.language,
                explanation=explanation,
            )

            no_banwords_headers = fixed.get_normalized(language=self.language)

            return no_banwords_headers.headers

        text_case: CaseCheck = await self.ai.instructor_request(
            prompt=FormattingPrompts.SENTENCE_CASE_CHECK_JSON.format(text=response.headers),
            output_schema=CaseCheck,
            assistant=getattr(FormattingPrompts, f"CASE_CHECK_JSON_ASSISTANT_{self.language.name}"),
            system=settings.ai.OPENAI_CASE_VERIFICATION_ROLE,
        )

        if text_case.correct_case:
            response = response.get_normalized(language=self.language)
            return response.headers

        explanation = (
            "\n".join(text_case.explanation) if isinstance(text_case.explanation, list) else text_case.explanation
        )

        fixed_headers: HeadersListSchema = await self.ai.replace_json_camel_case(
            input_text_object=response,
            output_schema=HeadersListSchema,
            language=self.language,
            explanation=explanation,
        )
        no_banwords_headers = fixed_headers.get_normalized(language=self.language)
        return no_banwords_headers.headers

    @staticmethod
    def convert_str_to_list(text: str) -> list[str]:
        if not text:
            return []

        return ast.literal_eval(text)

    async def create_h2_content(self, data: H2ContentInput) -> H2ContentOutput:
        h2_content = H2ContentOutput()
        ec = partial(ElementContent, tag=InformationalTagType.P, html=True, processed=True)

        system_prompt = IntentPrompts.get_system_prompt(intent=self.page_metadata.search_intent)
        content_template = IntentPrompts.get_content_template(intent=self.page_metadata.search_intent)
        prompt = content_template.format(
            keyword=self.cluster_keyword,
            topic=self.page_metadata.topic_name,
            country=self.target_country,
            language=self.language,
            n_words=data.n_words,
            h2_tags_number=data.h2_tags_number,
            summary=data.summary,
        )

        clean_prompt = strip_braces(prompt)

        response: ListElementOutput = await self.ai.gpt_request(
            prompt=clean_prompt,
            system=system_prompt.format(n_words=data.n_words, keyword=self.cluster_keyword),
            output_schema=ListElementOutput,
            temperature=0.8,
        )

        humanization_prompt = HumanizationPrompts.for_lang(language=self.language)

        humanized_content: ListElementOutput = await self.ai.instructor_request(
            prompt=humanization_prompt.format(
                content=response.data,
                language=self.language,
            ),
            output_schema=ListElementOutput,
        )

        no_ban_words_content: list[str] = remove_banwords(texts=humanized_content.data, language=self.language)
        content_list = [remove_links(text) for text in no_ban_words_content]

        h2_content.h2_data = [ec(content=content) for content in content_list]

        return h2_content

    async def create_related_pages_element(self, element_content: ElementContent) -> ElementContent:
        related_pages_content: list[ElementContent] = []

        ec = partial(ElementContent, position=element_content.position, processed=True)

        if self.page_metadata.has_parent:
            el = ec(tag="UPPER_RELATION")
            el.content = f'<a id="{self.page_metadata.parent_url}">{self.page_metadata.parent_topic}</a>'
            related_pages_content.append(el)

        if neighbours := self.page_metadata.neighbours:
            el = ec(tag="INNER_RELATION")

            for neighbour_id, neighbour_topic in neighbours:
                el.content += f'<a id="{neighbour_id}">{neighbour_topic}</a>'

            related_pages_content.append(el)

        if children := self.page_metadata.children:
            el = ec(tag="LOWER_RELATION")

            for child_id, child_topic in children:
                el.content += f'<a id="{child_id}">{child_topic}</a>'

            related_pages_content.append(el)

        element_content.children.extend(related_pages_content)

        if element_content.children:
            element_content.processed = True

        return element_content

    async def update_elements_by_context(self, elements: list[ElementContent], summary: str) -> list[ElementContent]:
        for element in elements:
            if element.tag in ("TITLE", "H1"):
                updated_metadata = await self.regenerate_page_metadata(summary)
                element.content = getattr(updated_metadata, element.tag.lower(), "")

            elif element.tag.startswith("IMG"):
                await self.create_image_content(element_content=element, summary=summary)

        return elements

    @staticmethod
    async def process_element(
        element_content: ElementContent | list[ElementContent],
    ) -> ElementContent | list[ElementContent]:
        match element_content:
            case list():
                for el in element_content:
                    el.processed = True

            case ElementContent():
                element_content.processed = True

        return element_content

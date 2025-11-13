import asyncio
import random
from datetime import datetime
from typing import Any
from uuid import uuid4

from aiohttp import ConnectionTimeoutError
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.tracers.context import tracing_v2_enabled
from langsmith import traceable
from loguru import logger
from pydantic import UUID4
from sentry_sdk import capture_exception
from treelib import Tree

from app.core.config import settings
from app.core.exc import (
    ClusterStructureCreateError,
    IndustryNotFoundException,
    InvalidKeywordException,
    MindmapFileValidationException,
)
from app.enums import (
    ClusterEventEnum,
    ElementPrompts,
    GenerationStatus,
    Language,
    MicroServiceType,
    PageContext,
    PageIntent,
    RequestType,
    StructurePrompts,
)
from app.models import Cluster
from app.schemas import XMindmapBase
from app.schemas.cluster.base import ClusterCreate, ClusterSettingsCreate
from app.schemas.elements import (
    BooleanElementOutput,
    ListElementOutput,
    StringElementOutput,
    UUIDElementOutput,
    page_elements_sample_mapper,
)
from app.schemas.elements.cluster_pages.samples import InformationalPageElementsParams
from app.schemas.page.cluster_page import ClusterPageCreate
from app.services.ai.base import AIBase
from app.services.ai.image_processing import ImageProcessor
from app.services.cluster.base import ClusterService
from app.services.microservices import MicroservicesClient
from app.services.next import XMindGeneratorService
from app.services.scraper import Scraper
from app.services.tavily_service import TavilyEnrichmentService
from app.utils import TextProcessing, UnitOfWork, UnitOfWorkNoPool
from app.utils.banwords import remove_banwords
from app.utils.convertors import capitalize_text_nodes, strip_braces
from app.utils.message_queue import enqueue_global_message
from app.utils.similarity_evaluation import SimilarityEvaluator
from app.utils.use_types import PageFuncType


class ClusterStructureGenerator(ClusterService):
    def __init__(self, user_id: UUID4, data: ClusterCreate, cluster_id: UUID4 = None) -> None:
        super().__init__()
        self.user_id = user_id
        self.cluster_id = cluster_id or uuid4()
        self.data = data
        self.ai = AIBase()
        self.image_processor = ImageProcessor()
        self.similarity_evaluator = SimilarityEvaluator()
        self.xmind_service = XMindGeneratorService()
        self.structure_tree = Tree()
        self.detected_page_intents: set[PageIntent] = set()
        self.geolocation_data: dict[str, str] = {}
        # Creation cluster progress variables
        self.completed_pages = 0
        self.min_time = 20

    async def close(self) -> None:
        await self.ai.close()
        await self.similarity_evaluator.close()

    async def __aenter__(self) -> "ClusterStructureGenerator":
        self.keyword_service = MicroservicesClient(MicroServiceType.GOOGLE_ADS)
        self.tavily = TavilyEnrichmentService()
        self.scraper = Scraper()

        self.ai = await self.ai.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type:ignore[no-untyped-def]
        await self.ai.__aexit__(None, None, tb)

        if exc_type:
            raise exc

    async def get_context(self, documents: list[Document]) -> PageContext:
        try:
            prompt = self.ai.construct_chat_prompt_template(human=ElementPrompts.SCRAPING_SUMMARIZATION_TEMPLATE)
            structured_llm = self.ai.summary_llm.with_structured_output(PageContext)
            chain = create_stuff_documents_chain(structured_llm, prompt)
            return await chain.ainvoke({"context": documents, "keyword": self.data.keyword})

        except Exception as e:
            capture_exception(e)
            return PageContext()

    async def search_third_party_sources(self, topic_name: str) -> list[Document]:
        """
        Searches for third-party sources related to the cluster page (topic) and
        creates a schema with additional information such as intent, category, and keywords.

        This method utilizes a scraper to gather search parameters based on the
        specified topic name and language, collects search results, and converts
        the data into a document format.

        Returns:
            list of documents representing the collected data if successful,
            or None if no data was found or an error occurred during the process.
        """
        try:
            search_params = self.scraper.get_search_params(query=topic_name, language=self.data.language)
            data = await self.scraper.collect_search(params=search_params)

            if data:
                parsed_documents = await self.scraper.get_documents(data=data)
                return self.scraper.h2_transformer.transform_documents(parsed_documents)

        except ConnectionTimeoutError:
            logger.warning("Connection timeout error occurred during search")

        except Exception as e:
            logger.exception(f"An unexpected error occurred: {e}")

        return []

    @traceable(tags=["STRUCTURE"])
    @staticmethod
    async def validate_keyword(keyword: str, language: Language) -> bool:
        """
        Check if keyword is correct

        Raises:
            InvalidKeywordException: if keyword is not correct

        """
        async with AIBase() as ai:
            response = await ai.gpt_request(
                prompt=StructurePrompts.KEYWORD_CORRECTNESS_CHECK,
                output_schema=BooleanElementOutput,
                keyword=keyword,
                language=language,
            )
        if not response.data:
            raise InvalidKeywordException(keyword=keyword)

        return response.data

    @traceable(tags=["STRUCTURE_INDUSTRY"])
    @staticmethod
    async def define_industry(keyword: str, language: Language) -> UUID4:
        """
        Calling OpenAI for select the best relevant industry for incoming keyword, language and description.

        Returns:
            Selected industry from chat

        Raises:
            IndustryNotFoundException: if answer from OpenAI does not exist in settings
        """
        async with UnitOfWork() as uow:
            industries = await uow.industry.get_multi()

        available_industries = {k: v.get_for_language(language) for k, v in industries.items()}

        async with AIBase() as ai:
            response = await ai.instructor_request(
                prompt=StructurePrompts.INDUSTRY_DEFINITION_TEMPLATE.format(
                    industries=available_industries,
                    keyword=keyword,
                ),
                assistant=StructurePrompts.INDUSTRY_DEFINITION_ASSISTANT,
                output_schema=UUIDElementOutput,
            )
        if response and str(response.data) in available_industries:
            return response.data

        raise IndustryNotFoundException(industry=response.data, industries=available_industries)

    @traceable(tags=["STRUCTURE_AUTHOR"])
    @staticmethod
    async def define_author(user_id: UUID4, industry_id: UUID4, keyword: str, language: Language) -> UUID4:
        """
        Calling OpenAI for select the best relevant author for incoming keyword, language and description.

        Returns:
            Selected author from chat
        """
        async with UnitOfWork() as uow:
            authors = await uow.author.get_all(
                created_by_id=user_id,
                industry_id=industry_id,
                language=language,
            )

        available_authors = [{"id": a.id, "education": a.education, "profession": a.profession} for a in authors]

        async with AIBase() as ai:
            response = await ai.instructor_request(
                prompt=StructurePrompts.AUTHOR_SELECTION_TEMPLATE.format(
                    authors=available_authors,
                    topic=keyword,
                ),
                output_schema=UUIDElementOutput,
            )

        if response and str(response.data) in available_authors:
            return response.data

        random_author = random.choice(authors)
        return random_author.id

    @traceable(tags=["STRUCTURE"])
    async def validate_mindmap(self, content: str) -> bool:
        response = await self.ai.gpt_request(
            prompt=StructurePrompts.MINDMAP_CORRECTNESS_CHECK, output_schema=BooleanElementOutput, content=content
        )

        return response.data

    @traceable(tags=["TITLE"])
    async def generate_main_title(self) -> str:
        """
        Generate topics for a given keyword by amount

        Returns:
            title generated by `keyword`
        """
        title: str = ""

        response: StringElementOutput = await self.ai.gpt_request(
            prompt=StructurePrompts.PAGE_NAME_GENERATION_TEMPLATE,
            assistant=StructurePrompts.PAGE_NAME_GENERATION_ASSISTANT,
            output_schema=StringElementOutput,
            keyword=self.data.keyword,
            language=self.data.language,
            country=self.data.target_country,
            current_date=datetime.now().strftime("%Y-%m"),
        )
        if not response:
            return title

        output = await self.ai.replace_string_camel_case(input_string=response.data, language=self.data.language)
        title_no_banwords: str = output.get_normalized(language=self.data.language)

        return title_no_banwords

    @traceable(tags=["TITLE"])
    async def generate_topic_name(self) -> str | None:
        """
        Generate topics for a given keyword by amount

        Returns:
            list with generated topics by `keyword`
        """

        response: StringElementOutput = await self.ai.gpt_request(
            prompt=StructurePrompts.TOPIC_NAME_GENERATION_TEMPLATE,
            assistant=StructurePrompts.TOPIC_NAME_GENERATION_ASSISTANT,
            output_schema=StringElementOutput,
            keyword=self.data.keyword,
            language=self.data.language,
            country=self.data.target_country,
        )
        if not response:
            return None

        reformated_title = await self.ai.replace_string_camel_case(
            input_string=response.data, language=self.data.language
        )
        topic_no_banwords: str = reformated_title.get_normalized(language=self.data.language)

        return topic_no_banwords

    @traceable(tags=["STRUCTURE"])
    async def generate_subtopics_names(self, topic: str, main_topic: str, temperature: float) -> list[str]:
        response: ListElementOutput = await self.ai.gpt_request(
            prompt=StructurePrompts.SUBTOPICS_NAMES_GENERATION_TEMPLATE,
            assistant=StructurePrompts.SUBTOPICS_NAMES_GENERATION_ASSISTANT,
            output_schema=ListElementOutput,
            request_type=RequestType.STRUCTURE,
            temperature=temperature,
            keyword=self.data.keyword,
            topic=topic,
            language=self.data.language,
            country=self.data.target_country,
            subtopic_context=str([node.data.topic for node in self.structure_tree.all_nodes()]),
            main_topic=main_topic,
        )

        if not response:
            return []

        subtopics = response.data

        response = await self.ai.replace_json_camel_case(
            input_text_object=subtopics,
            output_schema=ListElementOutput,
            language=self.data.language,
            explanation="",
        )

        subtopics_no_banwords: list[str] = response.get_normalized(language=self.data.language)

        return subtopics_no_banwords or subtopics

    async def _update_progress(
        self,
        pages_number: int,
        start_from: int = 0,
        coefficient: int = 1,
        message: str = "",
    ) -> None:
        """
        Calculate progress of cluster generation and send it to the client.

        Args:
            pages_number: number of pages to be generated
            start_from: initial progress value
            coefficient: coefficient for progress calculation
            message: message to be sent to the client

        WSEvents:
            - ClusterEventEnum.CREATING
        """

        self.completed_pages += 1

        await enqueue_global_message(
            event=ClusterEventEnum.CREATING,
            user_id=self.user_id,
            cluster_id=self.cluster_id,
            progress=round(start_from + (coefficient * self.completed_pages / pages_number), 2),
            message=message,
        )

    async def get_additional_pages_params(
        self,
        pages: list[ClusterPageCreate],
        initial_progress: int = 30,
        progress_coefficient: int = 70,
    ) -> None:
        """
        Call to google Ads service to define relevant category, intent and keyword for each topic.

        Args:
            pages: list with cluster pages
            initial_progress: initial progress value
            progress_coefficient: coefficient for progress calculation

        Returns:
            dict with keys as pages identifiers and values as page environment schema for each page(topic)
        """

        self.completed_pages = 0
        pages_count = len(pages)

        try:

            @traceable(tags=["STRUCTURE"])
            async def process_page(page: ClusterPageCreate) -> tuple[str, list]:
                relevant_keywords = await self.ai.generate_abstract_keywords(
                    page.topic, self.data.keyword, self.data.language, self.data.target_country
                )
                topic_keywords = await self.keyword_service.send(
                    "generate_keywords",
                    data=relevant_keywords,
                    lang_code=self.data.language.lang_code,
                    country_code=self.data.language.country_code,
                )

                page.keywords = topic_keywords or []
                documents = await self.search_third_party_sources(page.topic)

                h2_count_values = [d.metadata.get("h2_count", 0) for d in documents]
                p_words_values = [d.metadata.get("p_avg_words", 0) for d in documents]

                page.text_info.h2_tags_number = self.scraper._calculate_average(h2_count_values, default=3)
                n_words = self.scraper._calculate_average(
                    p_words_values, default=int(1500 / page.text_info.h2_tags_number)
                )
                page.text_info.n_words = max(50, n_words)
                context: PageContext = await self.get_context(documents)

                enriched_summary = await self.tavily.enrich_summary_with_facts(topic=page.topic)
                full_summary = context.summary + "\n\n" + enriched_summary

                page.text_info.summary = strip_braces(full_summary)
                page.search_intent = context.search_intent or PageIntent.INFORMATIONAL
                self.detected_page_intents.add(page.search_intent)

                await self._update_progress(
                    pages_number=pages_count,
                    start_from=initial_progress,
                    coefficient=progress_coefficient,
                    message=f"Generating additional params for page {page.topic}",
                )

                return str(page.id), page.keywords

            result = await asyncio.gather(*[process_page(page) for page in pages])

            keywords_by_topics = {k: v for (k, v) in result}

            categories_by_topics = (
                await self.keyword_service.send(
                    "get_categories_by_keywords",
                    keywords_by_topics=keywords_by_topics,
                    lang_code=self.data.language.lang_code,
                    country_code=self.data.language.country_code,
                )
                or {}
            )

            for page in pages:
                page.category = categories_by_topics.get(str(page.id), random.randint(2, 5))

        except Exception as e:
            capture_exception(e)
            logger.warning(f"Error occurred while generating additional pages params: {e}")

    @traceable(tags=["STRUCTURE"])
    async def generate_o1_mindmap(self, main_topic: str) -> dict[str, dict]:
        try:
            with tracing_v2_enabled():
                mindmap_content = None
                is_mindmap_valid = False

                mindmap_prompt = StructurePrompts.MINDMAP_GENERATION_TEMPLATE.format(
                    keyword=main_topic,
                    language=self.data.language,
                    country=self.data.target_country,
                    n_topics=self.data.max_pages,
                    current_date=datetime.now().strftime("%Y-%m"),
                )

                if self.data.max_pages > 5:
                    mindmap_content = await self.ai.o1_request(
                        prompt=mindmap_prompt,
                        n_topics=self.data.max_pages,
                    )
                    is_mindmap_valid = await self.validate_mindmap(mindmap_content)

                    if is_mindmap_valid:
                        logger.success("Generated mindmap using gpt-o1")
                    else:
                        logger.warning(f"Generated invalid mindmap: {mindmap_content}")

                if not is_mindmap_valid:
                    mindmap_content = await self.ai.unstructured_gpt_request(
                        prompt=mindmap_prompt,
                        n_topics=self.data.max_pages,
                    )
                    logger.success("Generated mindmap using gpt-4o")

                mindmap_string_object: StringElementOutput = await self.ai.replace_string_camel_case(
                    input_string=mindmap_content, mindmap=True, language=self.data.language
                )

                unparsed_mindmap = await self.ai.unstructured_gpt_request(
                    prompt=StructurePrompts.MINDMAP_STRUCTURING_TEMPLATE.format(
                        unstructured_mindmap=mindmap_string_object.data
                    ),
                    assistant=StructurePrompts.MINDMAP_STRUCTURING_ASSISTANT,
                    model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
                )

                if not unparsed_mindmap:
                    raise ClusterStructureCreateError

                no_banwords_mindmap: str = remove_banwords(texts=unparsed_mindmap, language=self.data.language)
                mindmap_dict = await TextProcessing.get_dict_from_string(no_banwords_mindmap)
                formatted_mindmap = capitalize_text_nodes(mindmap_dict)

                return formatted_mindmap

        except Exception:
            raise ClusterStructureCreateError

    async def fake_progress(self, coefficient: int, interval: float = 1.5) -> None:
        total_time = int(self.data.max_pages * interval)

        if total_time < self.min_time:
            interval = self.min_time / self.data.max_pages

        while self.completed_pages < self.data.max_pages:
            await asyncio.sleep(interval)
            await self._update_progress(
                pages_number=self.data.max_pages, coefficient=coefficient, message="Fake progress"
            )

    async def define_cluster_structure(self, main_topic: str) -> None:
        coefficient = 30
        fake_progress_task = asyncio.create_task(self.fake_progress(coefficient=coefficient))

        if self.data.max_pages == 1:
            o1_structure: dict = {main_topic: {}}

        else:
            o1_structure = await self.generate_o1_mindmap(main_topic=main_topic)

        try:
            fake_progress_task.cancel()

        except asyncio.CancelledError:
            pass

        finally:
            await enqueue_global_message(
                event=ClusterEventEnum.CREATING,
                user_id=self.user_id,
                cluster_id=self.cluster_id,
                progress=coefficient,
            )

        main_topic, main_topic_children = o1_structure.popitem()

        if geolocation := await self.image_processor.get_ai_geolocation(main_topic, self.data.target_country):
            self.geolocation_data["country"] = geolocation.country
            self.geolocation_data["city"] = geolocation.city

        self.structure_tree.create_node(
            tag=main_topic,
            identifier=main_topic,
            data=ClusterPageCreate(
                cluster_id=self.cluster_id,
                topic=main_topic,
            ),
        )
        await self.initialize_structure_tree(main_topic, main_topic_children)

    async def initialize_structure_tree(self, parent: str, children: dict[str, dict]) -> None:
        if self.data.max_pages == 1 or not children:
            return

        tasks = []

        for topic in children.keys():
            if self.structure_tree.get_node(topic):
                continue

            parent_node = self.structure_tree.get_node(parent)
            self.structure_tree.create_node(
                tag=topic,
                identifier=topic,
                parent=parent,
                data=ClusterPageCreate(
                    cluster_id=self.cluster_id,
                    topic=topic,
                    parent_id=parent_node.data.id,
                ),
            )
            tasks.append(self.initialize_structure_tree(topic, children[topic]))

        if tasks:
            await asyncio.gather(*tasks)

    def find_parent_ids_with_topics(self) -> list[ClusterPageCreate]:
        """
        Traverses generated topic structure and finds for each topic its parent.

        Returns:
            Distributed children topics with its single parent.

        Example:

            structure = {
                            '9bf526a0-fb72-4cfe-8706-e1843141550a': {
                                'topic': "L'univers des Hobbits",
                                'subtopics': {
                                    '02dd975c-0599-402b-bed0-02e1c9869ee6': {
                                        'topic': 'Les caractéristiques des habitations des Hobbits',
                                        'subtopics': {}
                                    }
                                }
                            },
                            ...
                        }
            Output:
                    {
                        '9bf526a0-fb72-4cfe-8706-e1843141550a': {
                            'topic': "L'univers des Hobbits",
                            'related_parent': None
                        },
                        '02dd975c-0599-402b-bed0-02e1c9869ee6': {
                            'topic': 'Les caractéristiques des habitations des Hobbits',
                            'related_parent': '9bf526a0-fb72-4cfe-8706-e1843141550a'
                        },
                        ...
                    }
        """
        parent_data: dict[str, ClusterPageCreate] = {}

        for node_id in self.structure_tree.expand_tree():
            node = self.structure_tree.get_node(node_id)
            parent_data[node.data.id] = node.data
            if self.structure_tree.parent(node_id):
                parent_data[node.data.id].parent_id = self.structure_tree.parent(node_id).data.id

        return list(parent_data.values())

    async def generate_cluster_topics(self, *_: Any, **__: Any) -> list[ClusterPageCreate]:
        main_topic = await self.generate_main_title()
        await self.define_cluster_structure(main_topic=main_topic)

        pages = self.find_parent_ids_with_topics()
        await self.get_additional_pages_params(pages=pages)

        return pages

    async def process_structure_file(self, file_data: list[XMindmapBase]) -> list[ClusterPageCreate]:
        """
        Generate pages for a cluster based on the structure of an uploaded mindmap file.

        Args:
            file_data: The uploaded mindmap file.

        Returns:
            A list of dictionaries representing the generated pages.

        Raises:
            MindmapPageCountMismatchException: If the mindmap page count does not match the expected value in `data`.
        """
        topic = file_data[0].topic

        response = await self.ai.instructor_request(
            prompt=StructurePrompts.XMIND_STRUCTURE_TOPIC_CORRECTNESS_CHECK.format(
                topic=topic, language=self.data.language
            ),
            assistant=StructurePrompts.XMIND_STRUCTURE_TOPIC_CORRECTNESS_CHECK_ASSISTANT,
            output_schema=BooleanElementOutput,
        )
        if not response.data:
            raise MindmapFileValidationException(user_id=self.user_id, topic=topic)

        pages = [
            ClusterPageCreate(
                id=obj.id,
                topic=obj.topic,
                cluster_id=self.cluster_id,
                parent_id=obj.parent_id,
            )
            for obj in file_data
        ]
        try:
            await self.get_additional_pages_params(
                pages=pages,
                initial_progress=0,
                progress_coefficient=100,
            )

        except Exception as e:
            logger.exception(e)

        return pages

    async def save_cluster_structure(self, pages: list[ClusterPageCreate]) -> None:
        async with UnitOfWorkNoPool() as uow:
            cluster_created: Cluster = await uow.cluster.get_one(
                id=self.cluster_id, join_load_list=[uow.cluster.settings_load]
            )
            cluster_created.topics_number = len(pages)
            cluster_created.status = GenerationStatus.STEP2

            await uow.session.flush()

            for intent in self.detected_page_intents:
                cluster_settings = page_elements_sample_mapper.get(intent, InformationalPageElementsParams)

                main_source_link: dict = {}

                if all([self.data.main_source_link, intent == PageIntent.INFORMATIONAL]):
                    main_source_link = self.data.main_source_link.model_dump()  # type: ignore

                db_obj = ClusterSettingsCreate(
                    cluster_id=cluster_created.id,
                    search_intent=intent,
                    main_source_link=main_source_link,
                    general_style=cluster_settings.general_style_sample,  # type: ignore
                    elements_params=cluster_settings.elements_param_sample,  # type: ignore
                    geolocation=self.geolocation_data,
                ).to_model()

                cluster_created.settings.append(db_obj)

            await uow.session.flush()
            await uow.page_cluster.create_bulk(pages=[page.model_dump() for page in pages])

    async def build_cluster_structure(self, file_data: list[XMindmapBase] = None) -> None:
        """
        Creation of cluster by defining industry, generating and creating relation between topics.

        Args:
            file_data: xmind parsed structure

        Raises:
            If any exception was raised, delete cluster and re-raise exception.

        WSEvents:
            If cluster was created, enqueue global message with CREATED event.
        """

        func: PageFuncType = self.process_structure_file if file_data else self.generate_cluster_topics
        pages = await func(file_data)

        await self.save_cluster_structure(pages=pages)

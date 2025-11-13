import re
from asyncio import gather
from itertools import chain
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from loguru import logger
from tavily import AsyncTavilyClient

from app.core import settings
from app.utils.concurrency import RPMSemaphore

MAX_INITIAL_RESULTS = 8
MAX_EXTRACT_URLS = 6
MAX_SUMMARY_RESULTS = 5
MIN_CONTENT_LENGTH = 40
MAX_FINAL_FACTS = 20

MIN_SENTENCE_LENGTH = 30
MIN_CLEAN_SENTENCE_LENGTH = 25
MIN_PARAGRAPH_LENGTH = 60
MAX_PARAGRAPH_LENGTH = 400
MIN_CLEAN_PARAGRAPH_LENGTH = 40
MAX_EXTRACTED_FACTS = 10

MIN_TOPIC_MATCH_RATIO = 0.2
MIN_VALUE_INDICATORS = 1
MIN_FACT_LENGTH = 15
MAX_FACT_LENGTH = 800
MAX_CLEAN_FACTS = 60
FACT_KEY_LENGTH = 20

MIN_FACT_CHAR_LENGTH = 25
MIN_WORD_COUNT = 4

SUMMARY_QUERY_TEMPLATE = (
    "Extract specific facts, statistics, steps, and practical "
    "information about {topic}.\n Focus on concrete data, numbers, "
    "procedures, and actionable information. Ignore social media, "
    "navigation, advertisements, publication details, references "
    "and author information."
)

GARBAGE_PATTERNS = frozenset(
    [
        "share on twitter",
        "share on facebook",
        "view all result",
        "no result",
        "home>",
        "byeric",
        "bychris",
        "published time",
        "open in a new tab",
        "find articles by",
        "error bars show",
        "values are means",
        "read more details",
        "copyright",
        "all rights reserved",
        "privacy policy",
        "terms of use",
    ]
)

VALUE_INDICATORS = frozenset(
    [
        "study",
        "research",
        "found",
        "showed",
        "demonstrated",
        "revealed",
        "participants",
        "patients",
        "trial",
        "analysis",
        "evidence",
        "effective",
        "treatment",
        "method",
        "procedure",
        "step",
        "process",
        "mg",
        "dose",
        "administration",
        "therapy",
        "clinical",
        "results",
        "significant",
        "improved",
        "reduced",
        "increased",
        "compared",
        "mechanism",
        "effect",
        "response",
        "outcome",
        "benefit",
        "first",
        "second",
        "then",
        "next",
        "start",
        "begin",
        "recommended",
        "should",
        "can",
        "may",
        "help",
        "works",
    ]
)

P = ParamSpec("P")
T = TypeVar("T")


class TavilyEnrichmentService:
    def __init__(self) -> None:
        self.client = AsyncTavilyClient(api_key=settings.scraper.TAVILY_API_KEY)
        self.concurrent_requests = settings.tavily_concurrent_requests

    async def enrich_summary_with_facts(self, topic: str) -> str:
        try:
            search_queries = self._generate_focused_queries(topic)
            ai_analyzed_facts = await self._get_ai_analyzed_facts(search_queries, topic)
            clean_facts = self._validate_and_clean_facts(ai_analyzed_facts)

            result = self._create_facts_only_output(clean_facts)
            print(result)
            return result

        except Exception as e:
            logger.error(f"Error in Tavily enrichment: {e}")
            return "**CURRENT FACTUAL DATA & INSIGHTS:**\n• Unable to retrieve additional factual data."

    @staticmethod
    def _generate_focused_queries(topic: str) -> list[str]:
        return [
            f"{topic} research studies statistics data methods facts",
            f"{topic} step by step guide practical instructions procedures",
        ]

    async def process_single_query(self, query: str, topic: str) -> list[str]:
        try:
            response = await self.client.search(
                query=query,
                search_depth="advanced",
                max_results=10,
                include_raw_content=True,
                include_domains=[
                    "edu",
                    "gov",
                    "org",
                    "pubmed.ncbi.nlm.nih.gov",
                    "nature.com",
                    "scholar.google.com",
                ],
                time_range="year",
            )

            if response.get("results"):
                return await self._get_summarized_facts(response["results"], topic, query)

        except Exception as e:
            logger.error(f"Error with query '{query}': {e}")

        return []

    async def _get_ai_analyzed_facts(self, queries: list[str], topic: str) -> list[str]:
        results = await gather(
            *[
                self.process_single_request_with_rate_limit(func=self.process_single_query, query=query, topic=topic)
                for query in queries
            ],
        )
        all_facts = list(chain.from_iterable(results))

        return all_facts

    @staticmethod
    async def process_single_request_with_rate_limit(
        func: Callable[P, Awaitable[T]], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        await rpm_limiter.acquire()
        try:
            data = await func(*args, **kwargs)
        finally:
            rpm_limiter.release()

        return data

    async def _get_summarized_facts(self, results: list[dict], topic: str, query: str) -> list[str]:
        try:
            urls = [result["url"] for result in results[:MAX_INITIAL_RESULTS]]

            if not urls:
                return []

            results_tuple = await gather(
                *[
                    self.process_single_request_with_rate_limit(
                        self.client.search,
                        query=SUMMARY_QUERY_TEMPLATE.format(topic=topic),
                        search_depth="advanced",
                        max_results=MAX_SUMMARY_RESULTS,
                        include_raw_content=True,
                    ),
                    self.process_single_request_with_rate_limit(self.client.extract, urls=urls[:MAX_EXTRACT_URLS]),
                ]
            )

            summary_response: dict[str, Any] | Exception = results_tuple[0]
            extract_response: dict[str, Any] | Exception = results_tuple[1]

            facts = []

            if isinstance(summary_response, dict) and (summary_results := summary_response.get("results", [])):
                summary_facts = self._process_summary_results(summary_results, topic)
                facts.extend(summary_facts)

            if isinstance(extract_response, dict) and (extract_results := extract_response.get("results", [])):
                extracted_facts = self._process_extract_results(extract_results, topic)
                facts.extend(extracted_facts)

            return facts[:MAX_FINAL_FACTS]

        except Exception as e:
            logger.debug(f"Summarization failed for {query}: {e}")
            return []

    def _process_summary_results(self, results: list[dict], topic: str) -> list[str]:
        facts = []
        for result in results:
            content = result.get("content")

            if content and len(content) > MIN_CONTENT_LENGTH:
                clean_content = self._clean_single_fact(content)
                if self._is_valuable_fact(clean_content, topic):
                    facts.append(clean_content)

        return facts

    def _process_extract_results(self, results: list[dict], topic: str) -> list[str]:
        facts = []
        for result in results:
            raw_content = result.get("raw_content")

            if raw_content:
                extracted_facts = self._extract_focused_facts(raw_content, topic)
                facts.extend(extracted_facts)

        return facts

    def _extract_focused_facts(self, content: str, topic: str) -> list[str]:
        facts = []

        sentences = content.split(". ")
        for sentence in sentences:
            sentence = sentence.strip()

            if len(sentence) > MIN_SENTENCE_LENGTH and self._is_valuable_fact(sentence, topic):
                clean_sentence = self._clean_single_fact(sentence)

                if len(clean_sentence) > MIN_CLEAN_SENTENCE_LENGTH:
                    facts.append(clean_sentence)

        paragraphs = content.split("\n\n")
        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if MIN_PARAGRAPH_LENGTH < len(paragraph) < MAX_PARAGRAPH_LENGTH and self._is_valuable_fact(
                paragraph, topic
            ):
                clean_paragraph = self._clean_single_fact(paragraph)

                if len(clean_paragraph) > MIN_CLEAN_PARAGRAPH_LENGTH:
                    facts.append(clean_paragraph)

        return facts[:MAX_EXTRACTED_FACTS]

    @staticmethod
    def _is_valuable_fact(text: str, topic: str) -> bool:
        text_lower = text.lower()

        if any(pattern in text_lower for pattern in GARBAGE_PATTERNS):
            return False

        topic_words = topic.lower().split()
        topic_match = sum(1 for word in topic_words if word in text_lower)
        if topic_match < len(topic_words) * MIN_TOPIC_MATCH_RATIO:
            return False

        value_count = sum(1 for indicator in VALUE_INDICATORS if indicator in text_lower)
        return value_count >= 1

    def _validate_and_clean_facts(self, facts: list[str]) -> list[str]:
        clean_facts = []
        seen_facts = set()

        for fact in facts:
            fact = re.sub(r"\s+", " ", fact).strip()
            fact = self._clean_single_fact(fact)

            if MIN_FACT_LENGTH < len(fact) < MAX_FACT_LENGTH:
                fact_key = fact[:FACT_KEY_LENGTH].lower()
                if fact_key not in seen_facts and not self._is_garbage_fact(fact):
                    seen_facts.add(fact_key)
                    clean_facts.append(fact)

        return clean_facts[:MAX_CLEAN_FACTS]

    @staticmethod
    def _clean_single_fact(fact: str) -> str:
        fact = re.sub(r"\[\d+\]", "", fact)
        fact = re.sub(r"<[^>]+>", "", fact)
        fact = re.sub(r"http[s]?://\S+", "", fact)
        fact = re.sub(r"\S+@\S+\.\S+", "", fact)
        fact = re.sub(r"doi:\s*/.*?(?=\s)", "", fact)
        fact = re.sub(r"PMID:\s*\d+", "", fact)
        fact = re.sub(r"Published Time:.*?\d{4}", "", fact)
        fact = re.sub(r"by[A-Z][a-z]+\s+[A-Z][a-z]+", "", fact)
        fact = re.sub(r"Share on.*?Facebook", "", fact)
        fact = re.sub(r"View All Result.*?Cannabis", "", fact)
        fact = re.sub(r"No Result.*?Result", "", fact)
        fact = re.sub(r"Open in a new tab", "", fact)
        fact = re.sub(r"Find articles by.*?(?=\s)", "", fact)
        fact = re.sub(r"Values are means.*?(?=\s)", "", fact)
        fact = re.sub(r"error bars show.*?(?=\s)", "", fact)
        fact = re.sub(r"Read more Details", "", fact)
        fact = re.sub(r"\s+", " ", fact)
        return fact.strip()

    @staticmethod
    def _is_garbage_fact(fact: str) -> bool:
        fact_lower = fact.lower()
        if any(term in fact_lower for term in GARBAGE_PATTERNS):
            return True

        if len(fact) < MIN_FACT_CHAR_LENGTH:
            return True

        word_count = len(fact.split())
        if word_count < MIN_WORD_COUNT:
            return True

        return False

    @staticmethod
    def _create_facts_only_output(facts: list[str]) -> str:
        if not facts:
            return "**CURRENT FACTUAL DATA & INSIGHTS:**\n• Limited specific data available for this topic."

        result = "**CURRENT FACTUAL DATA & INSIGHTS:**\n"
        result += "**Evidence-Based Information:**\n"

        for fact in facts:
            result += f"• {fact}\n"

        return result


rpm_limiter: RPMSemaphore = RPMSemaphore(settings.tavily_rpm_requests)

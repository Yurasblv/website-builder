from __future__ import annotations

import json
import random
from typing import Annotated, Any
from uuid import uuid4

import emoji
import instructor
from loguru import logger
from openai import AsyncOpenAI
from pydantic import UUID4, Base64Bytes, BaseModel, Field, field_validator, model_validator

from app.core.config import settings
from app.enums.base import Language
from app.utils.banwords import remove_banwords
from app.utils.convertors import remove_quotes, uppercase_first_letter

validation_client = instructor.from_openai(AsyncOpenAI(api_key=settings.ai.OPENAI_API_KEY))


class JSONSchemaMixin:
    @classmethod
    def json_schema(cls) -> str:
        """Return JSON schema for the model

        Example:
        class MyModel(BaseModel):
            name: str
            age: int
        """
        schema = cls.model_json_schema()  # type: ignore
        model_name = schema.get("title", cls.__name__)

        parts = [
            f"{field_name}: {cls.__parse_properties(data)}" for field_name, data in schema.get("properties", {}).items()
        ]

        return f"class {model_name}(BaseModel):\n\t" + "\n\t".join(parts)

    @classmethod
    def __parse_properties(cls, properties: dict[str, Any]) -> str:
        match properties.get("type"):
            case "string":
                return "str"
            case "integer":
                return "int"
            case "array":
                items = properties.get("items", {})
                return f"list[{cls.__parse_properties(items)}]"
            case "object":
                additionalProperties = properties.get("additionalProperties", {})
                return f"dict[str, {cls.__parse_properties(additionalProperties)}]"
            case "boolean":
                return "bool"
            case _:
                return "Any"


class BaseStyle(BaseModel):
    accentColor: str | None = ""
    backgroundColor: str | None = ""
    color: str | None = ""
    fontSize: str | None = ""
    fontWeight: str | None = ""
    borderRadius: str | None = ""
    border: str | None = ""
    fontFamily: str | None = ""

    @classmethod
    def sample(cls) -> BaseStyle:
        return cls(
            accentColor="#7792ff",
            backgroundColor="#ffffff",
            color="#000000",
            fontFamily="Arial",
        )


class ElementSettings(BaseModel):
    tableVariant: str | None = Field("", description="Table variant", examples=["horizontal", "vertical", "both"])
    graphVariant: str | None = Field("", description="Graph variant", examples=["bar", "line", "pie", "doughnut"])
    listVariant: str | None = ""
    language: str | None = ""
    image_alt_tag: str | None = ""
    content: str | None = ""
    bytes_content: Base64Bytes | None = None
    href: str | None = ""
    reference_follow: bool | None = Field(None, description="SEO attr for reference element to follow or not.")


class ElementStyleParam(BaseModel):
    type: str
    enabled: bool = True
    visible: bool = True
    position: int
    className: str | None = ""
    style: BaseStyle | None = BaseStyle()
    settings: ElementSettings | None = ElementSettings()


class ElementContent(BaseModel):
    """Contains results of generating pages"""

    content_id: str | UUID4 = Field(default_factory=uuid4)
    tag: str = Field(..., description="Tag type")
    position: int = 0
    classname: str | None = "default"
    style: BaseStyle | None = BaseStyle()
    href: str | None = ""
    html: bool = False
    settings: ElementSettings | None = ElementSettings()
    content: str = ""
    bytes_content: bytes | None = b""
    processed: bool = False
    children: list[ElementContent] = Field(default_factory=list, examples=[[]])

    def model_post_init(self, __context: Any) -> None:
        def migrate_content(e: "ElementContent") -> None:
            if e.settings:
                if not e.href and e.settings.href:
                    e.href = e.settings.href
                    e.settings.href = ""

                if not e.content and e.settings.content:
                    e.content = e.settings.content
                    e.settings.content = ""

                if not e.bytes_content and e.settings.bytes_content:
                    e.bytes_content = e.settings.bytes_content
                    e.settings.bytes_content = None

            if e.children:
                for child in e.children:
                    migrate_content(child)  # TODO: Is it possible to use super() here?

        migrate_content(self)


class H2ContentInput(BaseModel):
    summary: str
    n_words: int = 200
    h2_tags_number: int = 5


class H2ContentOutput(BaseModel):
    h2_data: list[ElementContent] = Field(default_factory=list)


class H2PositionInput(BaseModel):
    prompt: str
    injection_elements: list
    h2_elements: int


class BooleanElementOutput(BaseModel):
    data: bool = False


class ListElementOutput(BaseModel):
    data: list[str] = []

    def __bool__(self) -> bool:
        return bool(self.data)

    def model_dump_json(self, *, indent: int | None = None, **kwargs: Any) -> str:
        return json.dumps(self.data, indent=indent)

    def get_normalized(self, language: Language) -> list[str]:
        self.data = remove_banwords(self.data, language=language)
        return self.data


class StringElementOutput(BaseModel):
    data: str = ""

    def __bool__(self) -> bool:
        return bool(self.data)

    def get_normalized(self, language: Language, remove_quote: bool = True, upper_first_letter: bool = True) -> str:
        self.data = remove_banwords(self.data, language=language)

        if remove_quote:
            self.data = remove_quotes(self.data)

        if upper_first_letter:
            self.data = uppercase_first_letter(self.data)

        return self.data


class UUIDElementOutput(BaseModel):
    data: UUID4 = Field(default_factory=uuid4)


class DictElementOutput(BaseModel):
    data: dict = {}

    def __bool__(self) -> bool:
        return bool(self.data)

    def model_dump_json(self, *, indent: int | None = None, **kwargs: Any) -> str:
        return json.dumps(self.data, indent=indent)


class ImageAnnotationOutputSchema(BaseModel):
    """
    Pydantic schema representing image metadata.
    This image data will be used for generation via LLM.
    """

    image_annotation: str = Field(default="", description="Brief annotation of the image.")
    prompt: str = Field(
        default="",
        description="Prompt for the image that will be used as prompt for image generation.",
    )
    image_alt_tag: str = ""

    def __bool__(self) -> bool:
        return bool(self.prompt)

    def remove_banwords_annotation(self, language: Language = Language.US) -> "ImageAnnotationOutputSchema":
        return self.copy(update={"image_annotation": remove_banwords(self.image_annotation, language=language)})


class GraphElementSchema(BaseModel):
    labels: list[str]
    datasets: dict[str, Any] = {}

    @model_validator(mode="before")
    @classmethod
    def convert_to_str(cls, values: dict) -> dict:
        datasets = values.pop("datasets", {})

        values["datasets"] = {
            str(k): [str(v) for v in values] if isinstance(values, list) else values for k, values in datasets.items()
        }

        return values


class GraphOutputSchema(BaseModel):
    """
    Pydantic schema representing a graph or a chart.
    This graph will be displayed on the page.
    """

    label: Annotated[
        str,
        instructor.llm_validator(
            statement="Must be short phrase, suitable title for the chart on website. ",
            model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
            client=validation_client,
        ),
    ] = Field(default="")
    labels: list[str] = Field(..., description="List of options for the graph", min_length=4, max_length=6)
    data: list[int] = Field(..., description="Close to real-world data on the topic of the graph")

    def get_normalized(self, language: Language) -> "GraphOutputSchema":
        return self.copy(
            update={
                "label": remove_banwords(self.label, language=language),
                "labels": remove_banwords(self.labels, language=language),
            }
        )

    def transform_to_element(self) -> GraphElementSchema:
        return GraphElementSchema(
            labels=self.labels,
            datasets={
                "label": self.label,
                "data": [str(d) for d in self.data] if isinstance(self.data, list) else [str(self.data)],
            },
        )

    @model_validator(mode="before")
    @classmethod
    def convert_to_str(cls, values: dict) -> dict:
        data = values.pop("data", [])
        labels = values.pop("labels", [])
        values["data"] = [int(d) for d in data]
        values["labels"] = [str(label) for label in labels] if isinstance(labels, list) else [str(labels)]

        return values


class TableRow(BaseModel):
    column: str
    values: list[str]


class TableOutputSchema(BaseModel):
    title: Annotated[
        str,
        instructor.llm_validator(
            statement="Must be short sentence, suitable title for the table on website.",
            model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
            client=validation_client,
        ),
    ] = Field(default="")

    content: list[TableRow] = Field(
        default_factory=list,
        description="""
            The content of the table.
            Each key represents a name of a table column relevant to the generated title,
            and each key must contain meaningful values.
            Each value is a Python list with values strictly tied to the topic.
        """,
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_content(cls, data: dict) -> dict:
        raw_content = data.get("content", [])

        if isinstance(raw_content, list):
            data["content"] = [
                {
                    "column": str(item.get("column", "")),
                    "values": [str(v) for v in item.get("values", [])],
                }
                for item in raw_content
                if isinstance(item, dict)
            ]

        return data

    def get_normalized(self, language: Language) -> "TableOutputSchema":
        cleaned_content = [
            {
                "column": remove_banwords(row.column, language=language),
                "values": remove_banwords(row.values, language=language),
            }
            for row in self.content
        ]

        return self.copy(update={"title": remove_banwords(self.title, language=language), "content": cleaned_content})

    def __bool__(self) -> bool:
        return all([self.title, self.content])


class FAQItem(BaseModel):
    emojis: list[str] = Field(..., examples=[["🎰"]], description="List of emojis fitting the context of a QA pair")
    question: str = Field(
        ...,
        examples=["When's the best time to hit up Las Vegas?"],
        description="Question to be answered",
        max_length=185,
    )
    answer: str = Field(
        ...,
        examples=[
            "You'll wanna check out Las Vegas between March and May or September and November. \
                The weather's chill, and there's a bunch of cool events and shows going on."
        ],
        description="Answer to the question",
        max_length=185,
    )

    @field_validator("emojis")
    @classmethod
    def validate_emoji(cls, value: list[str]) -> list[str]:
        return [emoji.demojize(v) for v in value]

    @field_validator("question", "answer", mode="after")
    @classmethod
    def remove_quotes_and_uppercase_first_letter(cls, value: str) -> str:
        if len(value) > 185:
            raise ValueError(f"Text must be under 185 characters, got {len(value)}")
        return uppercase_first_letter(remove_quotes(value))


class FAQOutputSchema(BaseModel):
    """
    Pydantic schema representing a FAQ section on the website.
    This element will be displayed on the website. Must not be empty.
    """

    title: Annotated[
        str,
        instructor.llm_validator(
            statement="Must be short sentence, suitable title for the FAQ section on website. ",
            model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
            client=validation_client,
        ),
    ] = Field(default="")
    content: list[FAQItem] = Field(
        default_factory=list[FAQItem],
        description="The list of dicts where each dict contains a list of emojies, a question and an answer.",
    )

    def __bool__(self) -> bool:
        return all([self.title, self.content])

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return uppercase_first_letter(value)

    @model_validator(mode="after")
    def check_and_remove_duplicate_emojis(self) -> "FAQOutputSchema":
        all_seen_emojis = set()

        for i, item in enumerate(self.content):
            duplicates = []
            unique_emojis = []

            for emoji_text in item.emojis:
                if emoji_text in all_seen_emojis:
                    duplicates.append(emoji_text)
                else:
                    unique_emojis.append(emoji_text)
                    all_seen_emojis.add(emoji_text)

            if duplicates:
                logger.warning(
                    f"Duplicate emojis found in FAQ item {i + 1}: {', '.join(duplicates)}. These will be removed."
                )
                item.emojis = unique_emojis

        return self

    @field_validator("content")
    @classmethod
    def validate_content_count(cls, value: list[FAQItem]) -> list[FAQItem]:
        """
        Cut content to even number of items.
        """
        length = len(value)

        if length > 1 and length % 2:
            value.pop()

        return value

    def get_normalized(self, language: Language) -> "FAQOutputSchema":
        cleaned_content = [
            item.copy(
                update={
                    "question": remove_banwords(item.question, language=language),
                    "answer": remove_banwords(item.answer, language=language),
                }
            )
            for item in self.content
        ]

        return self.copy(update={"title": remove_banwords(self.title, language=language), "content": cleaned_content})


class QuizOutputSchema(BaseModel):
    """
    Pydantic schema representing a Quiz section on the website.
    This Quiz will be displayed on the website to improve user experience.
    """

    title: Annotated[
        str,
        instructor.llm_validator(
            statement="Must be short sentence, suitable title for the quiz on website. ",
            model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
            client=validation_client,
        ),
    ] = Field(default="")
    question: str = Field(..., description="The question of the quiz")
    answers: list[str] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="The answer options of the quiz where there is one right answer.",
    )
    rightAnswer: str = Field(
        ...,
        description="""The right answer for the quiz question. Must be a part of answers list""",
    )

    def __bool__(self) -> bool:
        return all([self.question, self.answers, self.rightAnswer])

    def get_normalized(self, language: Language) -> "QuizOutputSchema":
        return self.copy(
            update={
                "title": remove_banwords(self.title, language=language),
                "question": remove_banwords(self.question, language=language),
                "answers": remove_banwords(self.answers, language=language),
                "rightAnswer": remove_banwords(self.rightAnswer, language=language),
            }
        )

    @model_validator(mode="before")
    @classmethod
    def remove_quotes_and_uppercase_first_letter(cls, values: dict) -> dict:
        answers = values.pop("answers", [])

        for k, v in values.items():
            if isinstance(v, str):
                values[k] = uppercase_first_letter(remove_quotes(v))

        match answers:
            case list() | set() | tuple():
                values["answers"] = [uppercase_first_letter(remove_quotes(str(answer))) for answer in answers]

            case _:
                values["answers"] = [uppercase_first_letter(remove_quotes(str(answers)))]

        random.shuffle(values["answers"])
        return values


class FactItem(BaseModel):
    """
    Represents a single fact in a timeline or list of key points.
    """

    title: str = Field(
        ...,
        description="A short, descriptive label for the fact. Should be capitalized and concise (up to 15 words).",
        examples=["First Human in Space", "Moon Landing", "Invention of the Internet"],
    )
    fact: str = Field(
        ...,
        description="A factual statement or explanation corresponding to the title. Up to 3-4 sentences.",
        examples=[
            (
                "Apollo 11 astronauts landed on the Moon on July 20, 1969. "
                "Neil Armstrong became the first human to set foot on the lunar surface, followed by Buzz Aldrin. "
                "Their successful mission marked a major milestone in the space race and human exploration.",
            )
        ],
    )


class FactsOutputSchema(BaseModel):
    """
    Pydantic schema representing a facts section on the website.
    It is a block with interesting information on the topic.
    This section will be displayed on the website.
    """

    title: str = Field(
        ..., description="Must be short sentence or phrase, suitable title for the facts section on website."
    )
    description: str = Field(
        ...,
        description="""
            Brief summary of the key points related to the topic,
            with a minimum of 3 sentences and a maximum of 5 sentences.
        """,
    )
    timelines: list[FactItem] = Field(
        ...,
        description="""
            Python list of dicts, each dict has two keys: title and fact about this timeline point.
        """,
    )

    def __bool__(self) -> bool:
        return all([self.title, self.description, self.timelines])

    @field_validator("timelines")
    @classmethod
    def clean_timelines(cls, timelines: list[FactItem]) -> list[FactItem]:
        return [
            FactItem(
                title=uppercase_first_letter(remove_quotes(item.title)),
                fact=uppercase_first_letter(remove_quotes(item.fact)),
            )
            for item in timelines
        ]

    def get_normalized(self, language: Language) -> "FactsOutputSchema":
        cleaned_timelines = [
            FactItem(
                title=remove_banwords(item.title, language=language),
                fact=remove_banwords(item.fact, language=language),
            )
            for item in self.timelines
        ]

        return self.copy(
            update={
                "title": remove_banwords(self.title, language=language),
                "description": remove_banwords(self.description, language=language),
                "timelines": cleaned_timelines,
            }
        )


class ReferencesContentSchema(BaseModel):
    id: str
    href: str
    content: str


class UserMetadataSchema(BaseModel):
    name: str
    camera_brand: str
    camera_model: str


class GeolocationSchema(BaseModel):
    country: str
    city: str


class H2HeaderSchema(BaseModel):
    long: str
    short: str


class HeadersListSchema(BaseModel):
    headers: list[H2HeaderSchema]

    def get_normalized(self, language: Language) -> "HeadersListSchema":
        cleaned_headers = [
            H2HeaderSchema(
                long=remove_banwords(header.long, language=language),
                short=remove_banwords(header.short, language=language),
            )
            for header in self.headers
        ]
        return self.copy(update={"headers": cleaned_headers})


class CaseCheck(BaseModel):
    correct_case: bool
    explanation: str | list[str]


class PageMetadataSchema(BaseModel):
    title: str
    h1: str

    def remove_metadata_banwords(self, language: Language = Language.US) -> "PageMetadataSchema":
        return PageMetadataSchema(
            title=remove_banwords(self.title, language=language),
            h1=remove_banwords(self.h1, language=language),
        )


class BacklinkResponse(BaseModel):
    text: str = Field(..., description="Text containing a backlink")
    anchor: str = Field(..., description="Phrase to which a backlink will be attached")

    def get_normalized(self, language: Language) -> "BacklinkResponse":
        return self.model_copy(
            update={
                "text": remove_banwords(self.text, language=language),
                "anchor": remove_banwords(self.anchor, language=language),
            }
        )

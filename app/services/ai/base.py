import base64
import random
import re
from datetime import datetime
from typing import Any, Type, TypeVar

import httpx
import instructor
from instructor import AsyncInstructor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.utils import Output
from langchain_openai import ChatOpenAI
from langsmith.wrappers import wrap_openai
from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.enums import (
    Country,
    FormattingPrompts,
    IntentPrompts,
    Language,
    OpenAIPromptType,
    PageIntent,
    RequestType,
    StructurePrompts,
)
from app.schemas import ListElementOutput
from app.schemas.elements.cluster_pages.base import StringElementOutput, TableOutputSchema
from app.utils.decorators import retry_gpt_request, retry_image_request

OutputType = TypeVar("OutputType", bound=BaseModel)


class AIBase:
    def __init__(self) -> None:
        self.openai_client: AsyncOpenAI = wrap_openai(AsyncOpenAI(api_key=settings.ai.OPENAI_API_KEY))
        self.client: AsyncInstructor = instructor.from_openai(
            wrap_openai(AsyncOpenAI(api_key=settings.ai.OPENAI_API_KEY))
        )
        self.lc_llm: ChatOpenAI = ChatOpenAI(
            openai_api_key=settings.ai.OPENAI_API_KEY,
            model=settings.ai.OPENAI_MODEL_NAME,
        )
        self.lc_secondary_llm: ChatOpenAI = ChatOpenAI(
            openai_api_key=settings.ai.OPENAI_API_KEY,
            model=settings.ai.OPENAI_SECONDARY_MODEL_NAME,
        )
        self.summary_llm: ChatOpenAI = ChatOpenAI(openai_api_key=settings.ai.OPENAI_API_KEY, model="gpt-4.1-2025-04-14")
        self.message_pattern = f"Event({str(random.randint(0, 1000000))}) Closing connection to {{}} at {{}}"
        self.flux_headers = {
            "Authorization": f"Bearer {settings.ai.FLUX_API_KEY}",
            "Content-Type": "application/json",
        }

    async def __aenter__(self) -> "AIBase":
        """Context manager entry point."""
        return self

    async def close(self) -> None:
        """Close the connection to the DALL-E API."""
        if not self.client.client.is_closed:
            logger.info(self.message_pattern.format(id(self.client.client), datetime.now()))
            await self.client.client.close()

        if not self.lc_llm.root_client.is_closed:
            logger.info(self.message_pattern.format(id(self.lc_llm.root_client), datetime.now()))
            self.lc_llm.root_client.close()

        if not self.lc_secondary_llm.root_client.is_closed:
            logger.info(self.message_pattern.format(id(self.lc_secondary_llm.root_client), datetime.now()))
            self.lc_secondary_llm.root_client.close()

        if not self.lc_llm.root_async_client.is_closed:
            logger.info(self.message_pattern.format(id(self.lc_llm.root_async_client), datetime.now()))
            await self.lc_llm.root_async_client.close()

        if not self.lc_secondary_llm.root_async_client.is_closed:
            logger.info(self.message_pattern.format(id(self.lc_secondary_llm.root_async_client), datetime.now()))
            await self.lc_secondary_llm.root_async_client.close()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Context manager exit point."""
        try:
            await self.close()

        except Exception as e:
            logger.warning(e)

        if exc_type:
            raise exc

    # TODO splitting the logic
    @retry_image_request()
    async def generate_image_with_flux(
        self,
        prompt: str | None,
        model: str = "flux-pro/v1.1-ultra",
        image_size: tuple[int, int] = (1440, 1024),
        timeout: float = 15.0,
    ) -> bytes | None:
        """
        Send a request to the FLUX API.

        Args:
            prompt: The prompt for the FLUX API.
            model: AI Model for generating image
            image_size: The size of the image
            timeout: Timeout for the request

        Returns:
            image in bytes format or None of there is no prompt
        """

        if not prompt:
            return None

        payload = {
            "model": model,
            "prompt": prompt + " Without any text, words, numbers, or symbols.",
            "num_images": 1,
            "enable_safety_checker": True,
            "image_size": {"width": image_size[0], "height": image_size[1]},
            "sync_mode": False,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(settings.ai.FLUX_ENDPOINT, json=payload, headers=self.flux_headers)
            data = response.json()
            image_url = data["images"][0]["url"]
            image_response = await client.get(image_url)

        return image_response.content

    # TODO splitting the logic
    @retry_image_request()
    async def generate_image(
        self,
        prompt: str | None,
        model: str = "gpt-image-1",
        image_size: str = "1536x1024",
    ) -> bytes:
        """
        Send a request to the FLUX API.

        Args:
            prompt: The prompt for the FLUX API.
            model: AI Model for generating image
            image_size: The size of the image

        Returns:
            url of picture in string format
        """

        response = await self.openai_client.images.generate(
            model=model, prompt=prompt, size=image_size, quality="medium"
        )

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        return image_bytes

    async def generate_abstract_keywords(
        self, topic: str, keyword: str, language: Language, country: Country
    ) -> list[str]:
        response = await self.gpt_request(
            prompt=StructurePrompts.ABSTRACT_KEYWORD_GENERATION_TEMPLATE,
            assistant=StructurePrompts.ABSTRACT_KEYWORD_GENERATOR_ASSISTANT,
            output_schema=ListElementOutput,
            topic=topic,
            keyword=keyword,
            language=language,
            country=country,
        )

        return response.data if response else []

    async def get_pages_search_intents(self, keywords: dict[str, list[str]]) -> list[str]:
        generated_intents_list: list[str] = []

        response = await self.gpt_request(
            prompt=IntentPrompts.INTENT_DEFINITION_TEMPLATE,
            assistant=IntentPrompts.INTENT_DEFINITION_ASSISTANT,
            output_schema=ListElementOutput,
            keywords=keywords,
        )

        if not response:
            return generated_intents_list

        generated_intents_list.extend(response.data)
        for i, intent in enumerate(generated_intents_list):
            _intent = intent.upper()
            for right_intent in PageIntent.list():
                if right_intent in _intent:
                    generated_intents_list[i] = right_intent
        return generated_intents_list

    @retry_gpt_request(exc=(Exception,))
    async def gpt_request(
        self,
        *,
        prompt: OpenAIPromptType | str,
        output_schema: Type[BaseModel],
        context: str = None,
        assistant: OpenAIPromptType | str = None,
        system: OpenAIPromptType | str = settings.ai.OPEN_AI_ROLE,
        request_type: RequestType = RequestType.STANDART,
        temperature: float = 0.7,
        **params: Any,
    ) -> Output:
        """
        Send a request to OpenAI using langchain.

        Args:
            prompt: prompt for request
            output_schema: schema for response data
            context: additional information for request
            assistant: assisting information for request
            system: system information for request
            request_type: type of request
            temperature: temperature for request
            params: injection params for prompt

        Returns:
            response from the OpenAI converted to pydantic schema.
        """

        logger.debug("Call to OpenAI API")
        lc_prompt = self.construct_chat_prompt_template(
            human=prompt, assistant=assistant, system=system, context=context
        )

        if request_type == RequestType.STANDART:
            self.lc_llm.temperature = temperature
            structured_llm = self.lc_llm.with_structured_output(output_schema)

        else:
            self.lc_secondary_llm.temperature = temperature
            structured_llm = self.lc_secondary_llm.with_structured_output(output_schema)

        chain = lc_prompt | structured_llm
        output = await chain.ainvoke(params)

        return self.post_processing(output, output_schema)

    def post_processing(self, response: Output, schema: Type[BaseModel] | None = None) -> Output:
        """
        Processes the response from OpenAI by cleaning up the output data.

        Args:
            response: The raw response object from OpenAI.
            schema: Schema for response data

        Returns:
            The modified response object with cleaned data.
        """

        if schema is None:
            return self.clean_values(response)

        if isinstance(schema, TableOutputSchema):
            response.data = self.clean_values(response.data)

        return response

    def clean_values(self, data: Any) -> Any:
        """
        Extracts values for the 'Nom' key from dictionaries inside lists within the input data.

        Args:
            data: The response data to clean or extract values from.

        Returns:
            The modified response object with cleaned data.
        """

        match data:
            case list() if all(isinstance(item, dict) for item in data):
                return [v for item in data for v in item.values()]

            case dict():
                return {k: self.clean_values(v) for k, v in data.items()}

            case list():
                return [self.clean_values(item) for item in data]

            case str():
                match = re.search(r'content=["\'](.*?)["\']', data)
                return match.group(1).strip() if match else data

            case _:
                return data

    @staticmethod
    def construct_chat_prompt_template(
        *,
        human: str,
        assistant: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> ChatPromptTemplate:
        template_messages = [
            ("system", system or settings.ai.OPEN_AI_ROLE),
            ("human", human),
        ]
        if assistant:
            template_messages.append(("human", assistant))

        for m in kwargs.values():
            if m:
                template_messages.append(("human", m))

        return ChatPromptTemplate.from_messages(template_messages)

    @retry_gpt_request(exc=(Exception, ValidationError))
    async def instructor_request(
        self,
        *,
        prompt: OpenAIPromptType | str,
        output_schema: Type[OutputType],
        context: str = None,
        assistant: OpenAIPromptType | str = None,
        system: OpenAIPromptType | str = settings.ai.OPEN_AI_ROLE,
        temperature: float = 0.7,
        model: str = settings.ai.OPENAI_MODEL_NAME,
    ) -> OutputType:
        """
        Send a request to OpenAI using Instructor.

        Args:
            prompt: prompt for request
            output_schema: schema for response data
            context: additional information for request
            assistant: assisting information for request
            system: system information for request
            temperature: temperature for request
            model: model for request

        Returns:
            response from the OpenAI converted to pydantic schema.
        """
        logger.debug("Call to OpenAI API")
        template_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        if assistant:
            template_messages.append({"role": "user", "content": assistant})
        if context:
            template_messages.append({"role": "user", "content": context})
        response = await self.client.chat.completions.create(
            model=model,
            response_model=output_schema,
            messages=template_messages,
            temperature=temperature,
        )
        return response

    @retry_gpt_request(exc=(Exception,))
    async def o1_request(
        self,
        prompt: str,
        n_topics: int | None = None,
        context: str = None,
        assistant: OpenAIPromptType | str = None,
        system: OpenAIPromptType | str = settings.ai.OPEN_AI_ROLE,
    ) -> str:
        template_messages = [
            {"role": "user", "content": system},
            {"role": "user", "content": prompt},
        ]

        if n_topics:
            template_messages.append(
                {
                    "role": "user",
                    "content": f"Create exactly **{n_topics} topics (L1 root topic included)**, no more no less!",
                }
            )
        if assistant:
            template_messages.append({"role": "user", "content": assistant})
        if context:
            template_messages.append({"role": "user", "content": context})
        response = await self.openai_client.chat.completions.create(
            model=settings.ai.OPENAI_SMART_MODEL_NAME, messages=template_messages
        )
        return response.choices[0].message.content

    @retry_gpt_request(exc=(Exception,))
    async def o3_request(
        self,
        prompt: str,
        context: str = None,
        assistant: OpenAIPromptType | str = None,
        system: OpenAIPromptType | str = settings.ai.OPEN_AI_ROLE,
    ) -> str:
        template_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        if assistant:
            template_messages.append({"role": "user", "content": assistant})
        if context:
            template_messages.append({"role": "user", "content": context})

        response = await self.openai_client.responses.create(model="o3", input=template_messages)

        return response.output_text

    async def unstructured_gpt_request(
        self,
        *,
        prompt: str,
        n_topics: int | None = None,
        context: str = None,
        assistant: OpenAIPromptType = None,
        system: OpenAIPromptType | str = settings.ai.OPEN_AI_ROLE,
        temperature: float = 0.7,
        model: str = settings.ai.OPENAI_MODEL_NAME,
    ) -> str:
        logger.debug("Call to OpenAI API")
        template_messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        if n_topics:
            template_messages.append(
                {
                    "role": "user",
                    "content": f"Generate exactly **{n_topics} topics (L1 root topic included)**, no more no less!",
                }
            )
        if assistant:
            template_messages.append({"role": "assistant", "content": assistant})
        if context:
            template_messages.append({"role": "user", "content": context})
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=template_messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def replace_json_camel_case(
        self,
        input_text_object: BaseModel | list[str],
        output_schema: type[BaseModel],
        language: Language,
        explanation: str | list[str] | None = None,
    ) -> Any:
        if isinstance(input_text_object, list):
            text_input = input_text_object
        else:
            text_input = input_text_object.model_dump_json(warnings=False)

        formatted_text_schema = await self.instructor_request(
            prompt=FormattingPrompts.REPLACE_CAMEL_CASE_LIST_TEMPLATE.format(
                content=text_input,
                language=language,
                explanation=explanation,
            ),
            system=settings.ai.OPENAI_FORMATTING_ROLE,
            output_schema=output_schema,
            assistant=FormattingPrompts.REPLACE_CAMEL_CASE_LIST_ASSISTANT,
        )

        return formatted_text_schema

    async def replace_string_camel_case(
        self, input_string: str | None, language: Language, mindmap: bool = False
    ) -> StringElementOutput:
        formatted_string = await self.instructor_request(
            prompt=FormattingPrompts.REPLACE_CAMEL_CASE_TEMPLATE.format(
                content=input_string,
                language=language,
            ),
            system=settings.ai.OPENAI_FORMATTING_ROLE,
            output_schema=StringElementOutput,
            assistant=(
                FormattingPrompts.MINDMAP_FORMATTING_ASSISTANT
                if mindmap
                else FormattingPrompts.REPLACE_CAMEL_CASE_ASSISTANT
            ),
        )

        return formatted_string

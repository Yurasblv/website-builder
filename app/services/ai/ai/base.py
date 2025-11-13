import random
import re
from datetime import datetime
from typing import Any, Type, TypeVar

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
from app.enums import RequestType
from app.schemas import TableOutputSchema
from app.utils.decorators import retry_gpt_request

OutputType = TypeVar("OutputType", bound=BaseModel)


class AIBase:
    def __init__(self) -> None:
        self.openai_client: AsyncOpenAI = AsyncOpenAI(api_key=settings.ai.OPENAI_API_KEY)
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

    @retry_gpt_request(exc=(Exception,))
    async def gpt_request(
        self,
        *,
        prompt: str,
        output_schema: Type[BaseModel],
        context: str = None,
        assistant: str = None,
        system: str = settings.ai.OPEN_AI_ROLE,
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
        prompt: str,
        output_schema: Type[OutputType],
        context: str = None,
        assistant: str = None,
        system: str = settings.ai.OPEN_AI_ROLE,
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

    async def o1_request(
        self,
        prompt: str,
        n_topics: int | None = None,
        context: str = None,
        assistant: str = None,
        system: str = settings.ai.OPEN_AI_ROLE,
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

    async def unstructured_gpt_request(
        self,
        *,
        prompt: str,
        n_topics: int | None = None,
        context: str = None,
        assistant: str = None,
        system: str = settings.ai.OPEN_AI_ROLE,
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

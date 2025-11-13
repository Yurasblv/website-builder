from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableMap, RunnablePassthrough, RunnableSequence
from langchain_core.runnables.utils import Output

from app.services.ai import AIBase


class StaticRunnable(Runnable):
    def __init__(self, value: Any) -> None:
        self.value = value

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self.value


class ChainBuilder(AIBase):
    def __init__(self) -> None:
        super().__init__()
        self.chain_sequence: RunnableSequence | None = None
        self.first_recorded_input: dict[str, Any] = {}
        self.last_recorded_output: str = ""

    async def __aenter__(self) -> "ChainBuilder":
        """Context manager entry point."""
        self.reset_chain()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Context manager exit point."""
        self.reset_chain()
        await super().__aexit__(exc_type, exc, tb)

    def reset_chain(self) -> None:
        self.chain_sequence = None

    def add_chain_block(
        self,
        human_prompt: str,
        computed_output_name: str,
        prompt_input: dict[str, Any] | None = None,
        assistant_prompt: str | None = None,
        **messages: str | None,
    ) -> None:
        template = self.construct_chat_prompt_template(human=human_prompt, assistant=assistant_prompt, **messages)
        block_chain = template | self.lc_llm | StrOutputParser()

        if not self.chain_sequence:
            self.chain_sequence = block_chain
            self.first_recorded_input = prompt_input or {}
        else:
            prompt_input = prompt_input or {}
            wrapped_prompt_input = {key: StaticRunnable(value) for key, value in prompt_input.items()}

            template_input = RunnableMap({**wrapped_prompt_input, self.last_recorded_output: RunnablePassthrough()})

            self.chain_sequence = self.chain_sequence | template_input | block_chain

        self.last_recorded_output = computed_output_name

    async def invoke_chain(self) -> Output:
        self.chain_sequence = self.chain_sequence | StrOutputParser()

        if not self.chain_sequence:
            raise Exception("Chain has no steps.")

        output = await self.chain_sequence.ainvoke(self.first_recorded_input)

        return self.post_processing(output)

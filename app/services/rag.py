from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class RAGContext:
    def __init__(self) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.llm = ChatOpenAI(model_name="gpt-4-1106-preview", temperature=0, openai_api_key=settings.ai.OPENAI_API_KEY)

    async def get_context(self, source_text: str | None) -> str:
        """
        Retrieves a summarized context from a given source text.

        This function processes the provided source text by splitting it into smaller segments
        and then generating a summary using gpt-4-1106-preview.
        The text is divided into manageable chunks, each of which is processed to create a
        comprehend summary of the entire input.

        Args:
            source_text: customers input text from cluster description

        Returns:
            summarized version of description if it exists; otherwise None.
        """
        summary = ""
        if source_text:
            texts = self.text_splitter.split_text(source_text)
            docs = [Document(page_content=text) for text in texts]
            chain = load_summarize_chain(self.llm, chain_type="map_reduce")
            summary = chain.run(docs)
        return summary


rag_service = RAGContext()

from typing import TypeVar

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from backend.config import settings
from backend.logger import setup_logger

logger = setup_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class GeminiService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
            timeout=20,
            max_retries=1,
        )

    async def ainvoke_structured(
        self,
        prompt: ChatPromptTemplate,
        parser: PydanticOutputParser,
        **prompt_inputs,
    ) -> ModelT:
        chain = prompt | self.llm | parser
        return await chain.ainvoke(
            {
                **prompt_inputs,
                "format_instructions": parser.get_format_instructions(),
            }
        )

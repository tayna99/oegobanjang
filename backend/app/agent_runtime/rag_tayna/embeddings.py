from functools import lru_cache
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


@lru_cache(maxsize=1)
def get_embedding_model() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.openai_api_key,
    )

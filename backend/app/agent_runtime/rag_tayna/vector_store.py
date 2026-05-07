import os
from functools import lru_cache
from langchain_chroma import Chroma

from .embeddings import get_embedding_model

CHROMA_PERSIST_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..", ".chroma", "foreign_hiring"
    )
)
CHROMA_COLLECTION_NAME = "foreign_hiring"


@lru_cache(maxsize=1)
def get_chroma_store() -> Chroma:
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=CHROMA_PERSIST_DIR,
    )

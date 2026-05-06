from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def maybe_split(doc: Document) -> list[Document]:
    if len(doc.page_content) <= MAX_CHUNK_SIZE:
        return [doc]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_documents([doc])

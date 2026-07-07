"""Summarizer: rag_contexts가 많을 때 LLM 컨텍스트 초과를 방지합니다."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings

MAX_RAG_CHARS = 3000
_SYSTEM = "아래 텍스트를 핵심만 요약해주세요. 원문의 법조문 인용, 출처, 핵심 내용은 반드시 포함하세요."


def maybe_summarize_contexts(rag_contexts: list[dict]) -> list[dict]:
    """rag_contexts의 총 글자수가 MAX_RAG_CHARS를 초과하면 LLM으로 각 항목을 요약합니다."""
    total_chars = sum(len(ctx.get("content", "")) for ctx in rag_contexts)
    if total_chars <= MAX_RAG_CHARS:
        return rag_contexts

    settings = get_settings()
    if not settings.openai_api_key:
        # API 키 없으면 앞 MAX_RAG_CHARS/len 글자만 잘라서 반환
        limit = MAX_RAG_CHARS // max(len(rag_contexts), 1)
        return [
            {**ctx, "content": ctx.get("content", "")[:limit] + "...(요약 생략)"}
            for ctx in rag_contexts
        ]

    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        openai_api_key=settings.openai_api_key,
        max_tokens=300,
    )

    result = []
    for ctx in rag_contexts:
        content = ctx.get("content", "")
        if len(content) > 500:
            try:
                resp = llm.invoke([
                    SystemMessage(content=_SYSTEM),
                    HumanMessage(content=content[:2000]),
                ])
                content = resp.content
            except Exception:
                content = content[:500] + "...(요약 실패)"
        result.append({**ctx, "content": content})
    return result

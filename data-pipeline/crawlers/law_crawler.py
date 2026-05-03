"""
법제처 법령 크롤러 — Grade A (공식 법령)

수집 대상:
  - 출입국관리법 + 시행령 + 시행규칙
  - 외국인근로자고용법 + 시행령 + 시행규칙

수집 방식:
  Playwright (Chromium headless) — iframe 내부 JS 렌더링 후 조문 파싱

출력: data-pipeline/raw/laws/{파일명}.jsonl (조문 단위 chunk)
실행: python data-pipeline/crawlers/law_crawler.py
"""

import json
import re
import time
import logging
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "raw" / "laws"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVED_AT = date.today().isoformat()

TARGET_LAWS = [
    {
        "name": "출입국관리법",
        "url": "https://www.law.go.kr/법령/출입국관리법",
        "filename": "출입국관리법",
        "publisher": "법무부",
        "visa_type": ["E-9", "H-2", "E-7", "F-2", "D-10"],
    },
    {
        "name": "출입국관리법 시행령",
        "url": "https://www.law.go.kr/법령/출입국관리법시행령",
        "filename": "출입국관리법_시행령",
        "publisher": "법무부",
        "visa_type": ["E-9", "H-2", "E-7", "F-2", "D-10"],
    },
    {
        "name": "출입국관리법 시행규칙",
        "url": "https://www.law.go.kr/법령/출입국관리법시행규칙",
        "filename": "출입국관리법_시행규칙",
        "publisher": "법무부",
        "visa_type": ["E-9", "H-2", "E-7", "F-2", "D-10"],
    },
    {
        "name": "외국인근로자의 고용 등에 관한 법률",
        "url": "https://www.law.go.kr/법령/외국인근로자의고용등에관한법률",
        "filename": "외국인근로자고용법",
        "publisher": "고용노동부",
        "visa_type": ["E-9", "H-2"],
    },
    {
        "name": "외국인근로자의 고용 등에 관한 법률 시행령",
        "url": "https://www.law.go.kr/법령/외국인근로자의고용등에관한법률시행령",
        "filename": "외국인근로자고용법_시행령",
        "publisher": "고용노동부",
        "visa_type": ["E-9", "H-2"],
    },
    {
        "name": "외국인근로자의 고용 등에 관한 법률 시행규칙",
        "url": "https://www.law.go.kr/법령/외국인근로자의고용등에관한법률시행규칙",
        "filename": "외국인근로자고용법_시행규칙",
        "publisher": "고용노동부",
        "visa_type": ["E-9", "H-2"],
    },
]

# 본문 조문 패턴: 앞에 공백 있고, 조문번호와 내용이 같은 줄에 있음
# 예: " 제10조(체류자격) ① 체류자격은..."
# 목차 조문 패턴: 공백 없이 "제10조(체류자격)..." (내용 없거나 짧은 제목만)
BODY_ARTICLE_PATTERN = re.compile(r"^\s+(제\s*\d+조(?:의\s*\d+)?)\s*(?:\(([^)]+)\))?(.*)")


def parse_articles_from_text(text: str, law_meta: dict) -> list[dict]:
    """
    iframe 본문 텍스트에서 조문 단위 chunk 추출.
    본문 조문: 앞에 공백이 있고 내용이 같은 줄에 있는 라인을 기준으로 분할.
    """
    lines = text.split("\n")
    chunks = []

    current_no = None
    current_title = ""
    current_lines: list[str] = []

    def flush():
        if not current_no or not current_lines:
            return None
        content = "\n".join(l.strip() for l in current_lines if l.strip()).strip()
        if len(content) < 10:
            return None
        no_clean = re.sub(r"\s+", "", current_no)
        source_id = f"{law_meta['filename']}_{no_clean}"
        title = f"{law_meta['name']} {current_no}"
        if current_title:
            title += f"({current_title})"
        return build_chunk(source_id, title, content, law_meta, current_no, current_title)

    for line in lines:
        m = BODY_ARTICLE_PATTERN.match(line)
        if m:
            chunk = flush()
            if chunk:
                chunks.append(chunk)
            current_no = m.group(1).strip()
            current_title = m.group(2) or ""
            rest = m.group(3) or ""
            current_lines = [line.strip()] if rest.strip() else [line.strip()]
        elif current_no:
            current_lines.append(line)

    chunk = flush()
    if chunk:
        chunks.append(chunk)

    return chunks


def build_chunk(
    source_id: str,
    title: str,
    content: str,
    law_meta: dict,
    article_number: str,
    article_title: str,
) -> dict:
    metadata = {
        "source_id": source_id,
        "title": title,
        "publisher": law_meta["publisher"],
        "source_type": "official_law",
        "url": law_meta["url"],
        "retrieved_at": RETRIEVED_AT,
        "effective_date": None,
        "doc_type": "law",
        "article_number": article_number,
        "article_title": article_title,
        "mission_agent": ["visa_document_agent"],
        "visa_type": law_meta["visa_type"],
        "country": ["ALL"],
        "industry": ["ALL"],
        "risk_level": "high",
        "evidence_grade": "A",
    }
    return {"source_id": source_id, "title": title, "content": content, "metadata": metadata}


def save_chunks(chunks: list[dict], filename: str) -> Path:
    output_path = RAW_DIR / f"{filename}.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return output_path


def crawl_law_with_playwright(page, law_meta: dict) -> int:
    """법령 1개를 Playwright로 수집 → chunk 수 반환."""
    name = law_meta["name"]
    url = law_meta["url"]
    log.info(f"수집 시작: {name}")

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
    except Exception as e:
        log.error(f"  페이지 로드 실패: {e}")
        save_chunks([], law_meta["filename"])
        return 0

    # iframe 내부 텍스트 추출
    text = ""
    for frame in page.frames:
        if "lsInfoP" in frame.url:
            try:
                text = frame.inner_text("body")
                break
            except Exception as e:
                log.warning(f"  iframe 텍스트 추출 실패: {e}")

    if not text:
        log.error(f"  텍스트 수집 실패: {name}")
        save_chunks([], law_meta["filename"])
        return 0

    chunks = parse_articles_from_text(text, law_meta)

    if not chunks:
        log.error(f"  조문 파싱 실패 (0개): {name}")
        save_chunks([], law_meta["filename"])
        return 0

    output_path = save_chunks(chunks, law_meta["filename"])
    log.info(f"  저장 완료: {output_path.name} ({len(chunks)}개 chunk)")
    return len(chunks)


def main():
    log.info("=== law_crawler.py 시작 (Playwright) ===")
    log.info(f"저장 위치: {RAW_DIR}")
    log.info(f"수집 대상: {len(TARGET_LAWS)}개 법령\n")

    total = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for law_meta in TARGET_LAWS:
            count = crawl_law_with_playwright(page, law_meta)
            results.append({"name": law_meta["name"], "chunks": count, "filename": law_meta["filename"]})
            total += count
            time.sleep(2)

        browser.close()

    log.info("\n=== 수집 완료 ===")
    for r in results:
        status = "✅" if r["chunks"] > 0 else "❌"
        log.info(f"  {status} {r['name']}: {r['chunks']}개 chunk → {r['filename']}.jsonl")
    log.info(f"\n총 {total}개 chunk 수집")


if __name__ == "__main__":
    main()

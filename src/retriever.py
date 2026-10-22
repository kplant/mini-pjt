"""RAG 파이프라인: 외부 인물·회사 소개 자료(data/*.md)를 검색합니다.

- 임베딩: Amazon Titan Text Embeddings v2 (Bedrock, us-east-1)
- 벡터DB: Chroma (./chroma_db)
- 실제 서비스에서는 이 검색을 외부 인물 DB나 검색 API로 바꿀 자리입니다.

검색 전에 '누구에 관한 자료인가'를 먼저 확인합니다. 질문의 대상(사람이나 회사)에 해당하는
소개 자료가 없으면 벡터 검색을 하지 않고 no_answer를 돌려줍니다. 비슷하기만 한 다른 회사의
자료를 근거로 지어내지 않게 하기 위해서입니다.

모델과 벡터DB는 모듈 최상단이 아니라 함수 안에서 만듭니다(embeddings=None 주입 패턴).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PERSIST_DIR = ROOT / "chroma_db"
COLLECTION = "intro_docs"
EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
REGION = "us-east-1"
TOP_K = 3

# 대상 판정에서 빼는 일반 단어. 직책이나 '소개 자료'로는 대상을 가리지 않습니다.
GENERIC_WORDS = {
    "대표", "교수", "이사", "부사장", "전무", "상무", "과장", "차장", "대리", "팀장", "부장",
    "비서", "관리자", "소개", "자료", "회사", "최근", "소식",
}


def _default_embeddings():
    """Bedrock Titan 임베딩을 만듭니다. 호출할 때만 만들어 import 시점에 외부 연결을 하지 않습니다."""
    from langchain_aws import BedrockEmbeddings

    return BedrockEmbeddings(model_id=EMBED_MODEL_ID, region_name=REGION)


def _subject_tokens(text: str) -> set[str]:
    """대상 판정에 쓸 낱말(사람 성명, 회사·기관명)을 뽑습니다."""
    words = re.findall(r"[0-9A-Za-z가-힣]+", (text or "").replace("님", ""))
    return {w for w in words if len(w) >= 2 and w not in GENERIC_WORDS}


def load_documents(data_dir: Path = DATA_DIR) -> list:
    """소개 자료 문서를 읽습니다. 문서 첫 줄 제목에서 대상(subjects)을 뽑아 메타데이터로 둡니다."""
    from langchain_core.documents import Document

    docs = []
    for path in sorted(data_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
        docs.append(Document(
            page_content=text,
            metadata={"source": path.name, "title": title,
                      "subjects": json.dumps(sorted(_subject_tokens(title)), ensure_ascii=False)},
        ))
    return docs


def build_chunks(docs: list) -> list:
    """문서를 '## 섹션' 단위로 나눕니다. 조각마다 문서 제목을 앞에 붙여 누구에 관한 내용인지 남깁니다."""
    from langchain_core.documents import Document

    chunks = []
    for doc in docs:
        title = doc.metadata["title"]
        for section in re.split(r"\n(?=## )", doc.page_content):
            body = section.strip()
            if not body or body.startswith("# "):
                continue
            chunks.append(Document(page_content=f"[{title}]\n{body}", metadata=dict(doc.metadata)))
    return chunks


def build_vectorstore(embeddings=None, persist_dir: Path | None = PERSIST_DIR,
                      data_dir: Path = DATA_DIR, rebuild: bool = False):
    """소개 자료로 Chroma 벡터DB를 만듭니다. 이미 있으면 다시 쓰고, rebuild=True면 새로 만듭니다.

    persist_dir=None이면 메모리에만 둡니다(검증용).
    """
    from langchain_chroma import Chroma

    embeddings = embeddings or _default_embeddings()
    kwargs = {"collection_name": COLLECTION, "embedding_function": embeddings}
    if persist_dir is not None:
        kwargs["persist_directory"] = str(persist_dir)
    store = Chroma(**kwargs)
    if rebuild:
        store.reset_collection()
    if rebuild or not store.get(limit=1)["ids"]:
        store.add_documents(build_chunks(load_documents(data_dir)))
    return store


def match_sources(subject: str, data_dir: Path = DATA_DIR) -> list[str]:
    """대상(사람 성명이나 회사명)에 해당하는 소개 자료 파일명을 찾습니다."""
    wanted = _subject_tokens(subject)
    sources = []
    for doc in load_documents(data_dir):
        subjects = json.loads(doc.metadata["subjects"])
        # 'ABC사의'처럼 조사가 붙어도 찾도록 서로 포함되면 같은 대상으로 봅니다.
        if any(w in s or s in w for w in wanted for s in subjects):
            sources.append(doc.metadata["source"])
    return sources


def search_intro(store, subject: str, question: str, k: int = TOP_K,
                 data_dir: Path = DATA_DIR) -> dict:
    """대상의 소개 자료에서 질문과 관련된 조각을 찾습니다.

    반환: {"results": [{"source", "content"}]} 또는 대상 자료가 없으면 {"no_answer": True, ...}
    results는 응답의 contexts에 그대로 들어갑니다.
    """
    sources = match_sources(subject, data_dir)
    if not sources:
        return {"no_answer": True, "results": [],
                "reason": f"'{subject}'에 관한 소개 자료가 없습니다."}
    docs = store.similarity_search(question, k=k, filter={"source": {"$in": sources}})
    return {"results": [{"source": d.metadata["source"], "content": d.page_content} for d in docs]}


def build_search_tool(store=None):
    """일정 Agent가 쓰는 소개 자료 검색 도구를 만듭니다. store를 주지 않으면 Chroma를 엽니다."""
    from langchain_core.tools import tool

    store = store or build_vectorstore()

    @tool
    def tool_search_intro(subject: str, question: str) -> str:
        """외부 인물이나 그 회사의 소개 자료(경력, 회사 소개, 최근 소식, 지난 미팅 메모)를 검색합니다.
        subject는 대상의 성명 전체나 회사명(예: '박정우 대표', 'ABC사'), question은 알고 싶은 내용입니다.
        연락처·직책 같은 정해진 정보는 이 도구가 아니라 프로필 조회 도구를 씁니다."""
        return json.dumps(search_intro(store, subject, question), ensure_ascii=False)

    return tool_search_intro

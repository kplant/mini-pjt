"""HTTP 서버입니다. POST /query로 질문을 받아 run_query의 응답을 그대로 돌려줍니다.

실행: uvicorn src.app:app --port 8000
판정과 응답 형식은 src/agent.py가 맡고, 이 파일은 요청을 읽고 응답을 내보내는 일만 합니다.
"""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.agent import run_query

app = FastAPI(title="임원 일정 관리 Agent")


class QueryRequest(BaseModel):
    """POST /query 요청 본문입니다. question만 필수입니다.

    thread_id를 보내면 같은 user_id·thread_id의 이전 대화를 이어 갑니다(예: "2번으로 해줘").
    """

    question: str = Field(min_length=1)
    user_id: str = "sec-kim"
    thread_id: str | None = None
    base_date: date | None = None


@app.post("/query")
def query(req: QueryRequest) -> dict:
    """질문 하나를 처리해 {answer, contexts, trace}를 돌려줍니다.

    Bedrock 호출이 블로킹이라 async가 아닌 def로 두어 스레드풀에서 실행되게 합니다.
    """
    return run_query(req.question, req.user_id, req.base_date, thread_id=req.thread_id)

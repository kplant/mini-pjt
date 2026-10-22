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

    thread_id는 지금은 받기만 하고 쓰지 않습니다. 대화 기억(TASKS 2-1)에서 run_query에 넘깁니다.
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
    return run_query(req.question, req.user_id, req.base_date)

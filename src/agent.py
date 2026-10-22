"""메인 에이전트 그래프입니다.

지금은 모델 연결(TASKS 1-1), 조율 Agent 하나(TASKS 1-2), 응답 형식(TASKS 1-3), 대화 기억(TASKS 2-1)이 있습니다. Supervisor는 다음 작업에서 덧붙입니다.

모델은 후보 여러 개를 순서대로 두고, 앞의 모델이 실패하면 다음 후보로 넘어가 중단 없이 씁니다.
후보와 순서는 MODEL_IDS에 두며, .env의 BEDROCK_MODEL_IDS(쉼표로 구분)로 덮어쓸 수 있습니다.
모델은 모듈 최상단이 아니라 함수 안에서 만듭니다. import만으로 AWS 자격 증명을 요구하지 않게 하기 위해서입니다.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.db import DEFAULT_DB, ROOT, connect
from src.tools import Ctx, Requester, build_tools, load_requester

REGION = "us-east-1"
CHECKPOINT_DB = ROOT / "checkpoints.sqlite"

# 앞에서부터 차례로 씁니다.
MODEL_IDS = (
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-sonnet-4-6",
    "global.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "us.amazon.nova-pro-v1:0",
    "us.amazon.nova-2-lite-v1:0",
    "global.amazon.nova-2-lite-v1:0",
    "us.amazon.nova-lite-v1:0",
)


def model_ids() -> list[str]:
    """사용할 모델 후보 목록을 순서대로 돌려줍니다.

    .env의 BEDROCK_MODEL_IDS가 있으면 그 값을, 없으면 MODEL_IDS를 씁니다.
    """
    from dotenv import load_dotenv

    load_dotenv()
    raw = os.getenv("BEDROCK_MODEL_IDS", "")
    ids = [m.strip() for m in raw.split(",") if m.strip()]
    return ids or list(MODEL_IDS)


def make_model(model_id: str):
    """Bedrock 채팅 모델 하나를 만듭니다. 판정을 흔들지 않도록 temperature는 0입니다."""
    from dotenv import load_dotenv
    from langchain_aws import ChatBedrockConverse

    load_dotenv()
    return ChatBedrockConverse(model=model_id, region_name=REGION, temperature=0)


def get_text(message: Any) -> str:
    """응답에서 텍스트만 모읍니다. content가 블록 리스트로 오기도 합니다."""
    content = message.content if hasattr(message, "content") else message
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return str(content)


def check_models(ids: list[str] | None = None) -> list[dict]:
    """후보 모델마다 짧은 요청을 한 번 보내 지금 쓸 수 있는지 확인합니다.

    반환: [{"model_id", "ok", "latency_s", "reply", "error"}]
    한 모델이 실패해도 멈추지 않고 다음 모델을 확인합니다.
    """
    results = []
    for model_id in ids or model_ids():
        start = time.time()
        try:
            reply = get_text(make_model(model_id).invoke("OK라고만 답하세요."))
            results.append({"model_id": model_id, "ok": True, "latency_s": round(time.time() - start, 2),
                            "reply": reply.strip()[:20], "error": ""})
        except Exception as exc:  # noqa: BLE001 - 어떤 오류든 기록하고 다음 후보로 넘어갑니다
            results.append({"model_id": model_id, "ok": False, "latency_s": round(time.time() - start, 2),
                            "reply": "", "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
    return results


# ---------------------------------------------------------------------------
# 조율 Agent (TASKS 1-2)
# ---------------------------------------------------------------------------

WEEKDAYS = "월화수목금토일"

COORDINATION_PROMPT = """당신은 임원 일정 조율 담당입니다. 참석자 모두가 비어 있는 후보 시간을 찾아 안내합니다.

규칙
- 판정과 계산은 도구가 합니다. 후보 시간, 바쁨, 권한은 도구 결과만 믿고 직접 만들지 않습니다.
- 도구에 사람을 넘길 때는 성명 전체(예: 강민준 부사장)를 씁니다.
- 날짜는 아래 '날짜 안내'의 값을 YYYY-MM-DD 그대로 도구에 넘깁니다. 직접 계산하지 않습니다.
- 회의 길이를 말하지 않으면 duration_min을 넘기지 않아 도구의 기본값을 씁니다.
- 참석자는 요청에 나온 사람만으로 정하고 되묻지 않습니다. 한 명만 나와도 그 사람으로 바로 후보 시간을 찾습니다.
- 후보 시간은 tool_find_candidates 결과의 번호, 날짜, 시작~끝 시각을 그대로 전합니다.
- 도구 결과에 denied, no_answer, conflict가 있으면 reason을 그대로 전하고, notice가 있으면 함께 안내합니다.
- 일정 등록은 사용자가 후보를 고른 뒤에만 합니다.
- 사용자가 번호로 후보를 고르면 직전 tool_find_candidates 결과에서 그 번호의 start·end와 참석자로 tool_register_event를 호출합니다.
- 한국어로 짧게 답합니다.
"""


def date_hints(base: date) -> str:
    """상대 날짜를 코드로 미리 계산해 프롬프트에 넣을 안내문을 만듭니다."""
    def d(x: date) -> str:
        return f"{x.isoformat()}({WEEKDAYS[x.weekday()]})"

    monday = base - timedelta(days=base.weekday())
    next_monday = monday + timedelta(days=7)
    return (
        "날짜 안내\n"
        f"- 기준일(오늘): {d(base)}\n"
        f"- 내일: {d(base + timedelta(days=1))}\n"
        f"- 이번 주: {d(monday)} ~ {d(monday + timedelta(days=4))}\n"
        f"- 다음 주: {d(next_monday)} ~ {d(next_monday + timedelta(days=4))}\n"
    )


def requester_desc(ctx: Ctx) -> str:
    """요청자의 성명·역할·담당 임원을 한 줄로 만듭니다."""
    req = ctx.requester
    conn = connect(ctx.db_path)
    try:
        me = conn.execute("SELECT name, title FROM people WHERE id = ?", (req.id,)).fetchone()
        line = f"요청자: {me['name']} {me['title']}({req.role})"
        if req.role == "비서" and req.executive:
            ex = conn.execute("SELECT name, title FROM people WHERE id = ?", (req.executive,)).fetchone()
            line += f", 담당 임원: {ex['name']} {ex['title']}"
        return line + "\n"
    finally:
        conn.close()


_CHECKPOINTER = None


def _checkpointer():
    """대화 기억용 SqliteSaver를 처음 쓸 때 한 번 만들어 재사용합니다.

    FastAPI가 요청을 스레드풀에서 처리하므로 check_same_thread=False로 엽니다.
    """
    global _CHECKPOINTER
    if _CHECKPOINTER is None:
        from langgraph.checkpoint.sqlite import SqliteSaver

        _CHECKPOINTER = SqliteSaver(sqlite3.connect(CHECKPOINT_DB, check_same_thread=False))
    return _CHECKPOINTER


def build_coordination_agent(ctx: Ctx, llm=None, checkpointer=None):
    """조율 Agent를 만듭니다. 도구는 ctx의 요청자로 고정되어 권한을 직접 검사합니다.

    checkpointer가 있으면 thread_id별로 대화를 이어 갑니다. 시스템 프롬프트는 대화 상태에 저장되지 않아 매 턴 새로 만듭니다.
    """
    from langchain.agents import create_agent

    prompt = COORDINATION_PROMPT + "\n" + date_hints(ctx.base_date) + "\n" + requester_desc(ctx)
    return create_agent(
        model=llm or make_model(model_ids()[0]),
        tools=build_tools(ctx)["조율"],
        system_prompt=prompt,
        checkpointer=checkpointer,
    )


def _invoke(agent, question: str, config: dict | None = None) -> list:
    """Agent를 실행하고 이번 턴의 메시지만 돌려줍니다.

    대화 기억이 있으면 결과에 이전 턴 메시지도 들어 있어, 마지막 사람 메시지부터 잘라 냅니다.
    """
    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config=config)
    messages = result["messages"]
    last_human = max((i for i, m in enumerate(messages) if getattr(m, "type", "") == "human"), default=0)
    return messages[last_human:]


# ---------------------------------------------------------------------------
# 응답 형식 (TASKS 1-3, 1-4): answer / contexts[{doc_id, text}] / trace[{step, input, output}]
# 판정 값은 모델의 답변 문장이 아니라 도구 결과만으로 정하고, trace의 decision 단계에 담습니다.
# ---------------------------------------------------------------------------

def collect_tool_calls(messages: list, agent_name: str) -> list[dict]:
    """AI 메시지의 도구 호출과 그 결과(ToolMessage)를 짝지어 [{agent, tool, args, result}]로 만듭니다."""
    results = {m.tool_call_id: m.content for m in messages if getattr(m, "type", "") == "tool"}
    calls = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            raw = results.get(tc["id"], "")
            try:
                result = json.loads(get_text(raw) if not isinstance(raw, str) else raw)
            except (json.JSONDecodeError, TypeError):
                result = {"raw": raw}
            calls.append({"agent": agent_name, "tool": tc["name"], "args": tc["args"], "result": result})
    return calls


def _merge_unique(calls: list[dict], key: str) -> list:
    """도구 결과의 목록 값을 순서를 지켜 중복 없이 모읍니다."""
    out = []
    for c in calls:
        for v in c["result"].get(key) or []:
            if v not in out:
                out.append(v)
    return out


def judge(calls: list[dict], route: str | None, model_id: str | None, latency_s: float) -> dict:
    """도구 결과로 판정 값을 만듭니다. 모델의 답변 문장은 보지 않습니다."""
    candidate_calls = [c for c in calls if c["tool"] == "tool_find_candidates"]
    return {
        "route": route,
        "refused": any(c["result"].get("denied") for c in calls),
        "no_answer": any(c["result"].get("no_answer") for c in calls),
        "candidates": candidate_calls[-1]["result"].get("candidates", []) if candidate_calls else [],
        "registered_for": _merge_unique(calls, "registered_for"),
        "pending_approvals": _merge_unique(calls, "pending_approval_for"),
        "model": model_id,
        "latency_s": round(latency_s, 2),
    }


def ensure_notices(answer: str, calls: list[dict]) -> str:
    """도구가 준 안내(notice)와 찾는 대상이 없는 이유(no_answer의 reason)가 답변에 빠졌으면 끝에 덧붙입니다.

    문구는 도구 결과 그대로 쓰고, 모델의 답변 문장은 고치지 않습니다.
    """
    lines = []
    for c in calls:
        texts = [c["result"].get("notice")]
        if c["result"].get("no_answer"):
            texts.append(c["result"].get("reason"))
        for t in texts:
            if t and t not in answer and t not in lines:
                lines.append(t)
    return "\n\n".join([answer, *lines]) if lines else answer


def _step(step: str, input_: Any, output: Any) -> dict:
    """trace 단계 하나. 제출 스펙대로 step·input·output 세 키만 둡니다."""
    return {"step": step, "input": input_, "output": output}


def build_trace(question: str, calls: list[dict], verdict: dict) -> list[dict]:
    """trace를 단계 목록으로 만듭니다: route → 도구 호출들 → decision(판정 값)."""
    steps = [_step("route", question, verdict["route"])]
    steps += [_step(f"{c['agent']}.{c['tool']}", c["args"], c["result"]) for c in calls]
    steps.append(_step("decision", "도구 결과로 판정", verdict))
    return steps


def decision(trace: list[dict]) -> dict:
    """trace에서 decision 단계의 판정 값을 꺼냅니다. 평가기와 테스트가 씁니다."""
    for s in reversed(trace):
        if s["step"] == "decision":
            return s["output"]
    return {}


def build_contexts(calls: list[dict]) -> list[dict]:
    """답변의 근거가 된 도구 결과를 [{doc_id, text}]로 담습니다."""
    return [{"doc_id": c["tool"], "text": json.dumps(c["result"], ensure_ascii=False)} for c in calls]


def _result(answer: str, contexts: list[dict], trace: list[dict]) -> dict:
    """응답 dict를 만듭니다. 제출 규약의 세 키 말고는 넣지 않습니다."""
    return {"answer": answer, "contexts": contexts, "trace": trace}


def _to_date(value: date | str | None) -> date:
    """기준일을 date로 바꿉니다. 없으면 오늘입니다."""
    if value is None:
        return date.today()
    return value if isinstance(value, date) else date.fromisoformat(value)


def run_query(question: str, user_id: str = "sec-kim", base_date: date | str | None = None,
              thread_id: str | None = None, llm=None, db_path: Path | str = DEFAULT_DB) -> dict:
    """질문 하나를 처리해 제출 스펙의 응답을 돌려줍니다. 지금은 조율 Agent 하나만 씁니다.

    thread_id가 있으면 같은 user_id·thread_id의 이전 대화를 이어 갑니다(checkpoints.sqlite).
    대화 키에 user_id를 붙여, 다른 사람이 같은 thread_id를 보내도 앞사람의 대화를 이어받지 못하게 합니다.
    thread_id가 없으면 기억 없이 한 번만 처리합니다.

    반환: {"answer": str,
           "contexts": [{"doc_id", "text"}],
           "trace": [{"step", "input", "output"}]}  # 마지막 decision 단계에 판정 값
    """
    start = time.time()
    requester: Requester | None = load_requester(user_id, db_path)
    if requester is None:
        verdict = judge([], None, None, time.time() - start)
        verdict["refused"] = True
        trace = [_step("auth", user_id, "등록되지 않은 사용자"), _step("decision", "요청자 확인", verdict)]
        return _result("등록되지 않은 사용자입니다. 요청을 처리할 수 없습니다.", [], trace)
    ctx = Ctx(requester, _to_date(base_date), Path(db_path))
    model_id = "injected" if llm is not None else model_ids()[0]
    checkpointer, config = None, None
    if thread_id:
        checkpointer = _checkpointer()
        config = {"configurable": {"thread_id": f"{user_id}:{thread_id}"}}
    messages = _invoke(build_coordination_agent(ctx, llm, checkpointer), question, config)
    calls = collect_tool_calls(messages, "조율")
    verdict = judge(calls, "조율", model_id, time.time() - start)
    answer = ensure_notices(get_text(messages[-1]), calls)
    return _result(answer, build_contexts(calls), build_trace(question, calls, verdict))


if __name__ == "__main__":
    for r in check_models():
        status = "OK  " if r["ok"] else "FAIL"
        print(f"{status} {r['latency_s']:>5}s  {r['model_id']:<52} {r['reply'] or r['error']}")

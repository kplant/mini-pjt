"""시연 스크립트입니다. 실행 중인 서버(POST /query)에 시연 5단계(TASKS 6-5)의 요청 8개를 차례로 보냅니다.

순서: 브리핑 → 조율(후보 → "2번으로 해줘")·프로필 → 승인 → 거절 2건
실행: 먼저 서버를 띄우고(uvicorn src.app:app --port 8000) 다른 창에서 python demo.py
      [--url http://localhost:8000] [--no-pause] [--no-warmup]
시작할 때 DB를 초기화하고, 첫 요청의 느린 시작(ADR 0005)을 녹화 전에 치르도록 예열 요청을 한 번 보냅니다.
단계마다 Enter를 눌러 넘어가므로 화면 녹화 속도에 맞출 수 있습니다.
"""

import argparse
import json
import sys
import time
import urllib.request
import uuid

from src.db import reset_db

BASE_DATE = "2026-10-26"  # 평가셋 고정 데이터의 기준일(월)

# (단계 제목, 요청자, 질문, 같은 대화로 이어 갈 대화 이름 또는 None, 화면에서 보여 줄 점)
STEPS = [
    ("1. 브리핑", "sec-kim", "내일 강민준 부사장님 일정 브리핑해줘", None,
     "비공개 일정(건강검진)은 '바쁨'으로만 보입니다."),
    ("2-1. 조율: 후보 시간", "sec-kim", "다음 주에 강민준 부사장님과 윤서연 전무님 1시간 회의 잡아줘", "coord",
     "참석자 모두가 비어 있는 후보 시간 3개를 코드가 계산합니다."),
    ("2-2. 조율: 후보 선택", "sec-kim", "2번으로 해줘", "coord",
     "같은 대화를 이어 등록합니다. 다른 임원(윤서연 전무)은 승인 대기입니다."),
    ("2-3. 프로필: 외부 인물", "sec-kim", "ABC사 박정우 대표는 어떤 분이야?", None,
     "소개 자료를 검색해 근거 문서(contexts)와 함께 답합니다."),
    ("3-1. 승인: 목록", "exec-yoon", "승인 대기 목록 보여줘", "approve",
     "2-2에서 생긴 참석 요청이 윤서연 전무에게 와 있습니다."),
    ("3-2. 승인: 처리", "exec-yoon", "회의 참석 요청 승인해줘", "approve",
     "윤서연 전무가 직접 승인합니다."),
    ("4-1. 거절: 담당 밖 일정", "sec-kim", "목요일 윤서연 전무님 인사위원회 안건이 뭐야?", None,
     "담당 비서가 아니라 도구가 거절하고, 안건은 나오지 않습니다."),
    ("4-2. 거절: 관리자", "admin-jo", "강민준 부사장 내일 일정 보여줘", None,
     "관리자는 일정을 볼 수 없습니다."),
]

# 녹화 전 예열: 일정을 바꾸지 않는 조회와 소개 자료 검색(처음 검색할 때 벡터DB를 여는 시간을 미리 치름)
WARMUP = [("exec-kang", "내일 내 일정 알려줘"), ("exec-kang", "한국대학교 고은비 교수 연구 분야가 뭐야?")]


def post(url: str, body: dict) -> tuple[dict, float]:
    """POST /query를 보내고 (응답, 걸린 초)를 돌려줍니다."""
    req = urllib.request.Request(f"{url}/query", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8")), time.time() - start


def summary(resp: dict) -> str:
    """decision 단계의 판정 값과 근거 문서를 한 줄로 줄입니다."""
    d = next((s["output"] for s in reversed(resp["trace"]) if s["step"] == "decision"), {})
    parts = [f"route={d.get('route')}", f"refused={d.get('refused')}"]
    if d.get("candidates"):
        parts.append("후보=" + ", ".join(f"{c['start'][5:10]} {c['start'][11:]}~{c['end'][11:]}" for c in d["candidates"]))
    if d.get("registered_for"):
        parts.append(f"등록={d['registered_for']}")
    if d.get("pending_approvals"):
        parts.append(f"승인 대기={d['pending_approvals']}")
    docs = sorted({c["doc_id"] for c in resp["contexts"] if c["doc_id"].endswith(".md")})
    if docs:
        parts.append(f"근거 문서={docs}")
    return " | ".join(parts)


def main() -> None:
    """DB 초기화와 예열 뒤 시연 단계를 차례로 실행합니다."""
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="임원 일정 관리 Agent 시연")
    parser.add_argument("--url", default="http://localhost:8000", help="서버 주소")
    parser.add_argument("--no-pause", action="store_true", help="단계 사이에 Enter를 기다리지 않음")
    parser.add_argument("--no-warmup", action="store_true", help="예열 요청을 보내지 않음")
    args = parser.parse_args()

    if not args.no_warmup:
        print("예열 요청을 보내는 중입니다(녹화 전 준비)…", flush=True)
        for user_id, question in WARMUP:
            post(args.url, {"question": question, "user_id": user_id, "base_date": BASE_DATE})
    reset_db()
    run_id = uuid.uuid4().hex[:6]  # 대화 기억이 이전 시연과 섞이지 않게 합니다
    print(f"DB를 초기화했습니다. 기준일 {BASE_DATE}(월)\n")

    total = time.time()
    for title, user_id, question, thread, point in STEPS:
        if not args.no_pause:
            input(f"[Enter] {title}")
        body = {"question": question, "user_id": user_id, "base_date": BASE_DATE}
        if thread:
            body["thread_id"] = f"demo-{run_id}-{thread}"
        print(f"\n━━ {title} ━━  ({point})")
        print(f"  요청자 {user_id}: {question}")
        resp, sec = post(args.url, body)
        print("  답변:")
        print("    " + resp["answer"].replace("\n", "\n    "))
        print(f"  판정: {summary(resp)} | {sec:.1f}초")
    print(f"\n시연 끝. 요청 {len(STEPS)}개, 전체 {time.time() - total:.0f}초(Enter 대기 포함)")


if __name__ == "__main__":
    main()

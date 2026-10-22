"""평가 문항 시나리오를 LLM 없이 도구로 직접 재현해 권한·승인 규칙과 RAG 대상 판정을 확인합니다.

실행: python evaluation/check_tools.py
실제 DB(schedule.sqlite)는 건드리지 않고 임시 폴더의 DB를 씁니다.
실패가 하나라도 있으면 종료 코드 1을 돌려줍니다.
"""
import sys
import tempfile
from datetime import date
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src import db, tools as T  # noqa: E402

DB = Path(tempfile.gettempdir()) / "mini_pjt_check_tools.sqlite"
BASE = date(2026, 10, 26)
fails = []


def ctx(uid):
    db.reset_db(DB)
    return T.Ctx(T.load_requester(uid, DB), BASE, DB)


def keep(uid):  # 초기화 없이 이어서
    return T.Ctx(T.load_requester(uid, DB), BASE, DB)


def q(sql):
    c = db.connect(DB)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name, "" if cond else detail)
    if not cond:
        fails.append(name)


def text(r):
    import json
    return json.dumps(r, ensure_ascii=False)


r = T.list_events(ctx("sec-kim"), "강민준 부사장님", "2026-10-27")
check("m-01", not r.get("denied") and "주간 경영회의" in text(r) and "ABC사 미팅" in text(r)
      and "바쁨" in text(r) and "건강검진" not in text(r), text(r))
r = T.list_events(ctx("exec-kang"), "강민준", "2026-10-27")
check("m-02", "건강검진" in text(r) and "주간 경영회의" in text(r), text(r))
r = T.list_events(ctx("sec-park"), "윤서연 전무", "2026-10-29")
check("m-03", not r.get("denied") and "인사위원회" in text(r) and "바쁨" in text(r) and "가족 행사" not in text(r), text(r))
r = T.find_candidates(ctx("sec-kim"), ["강민준 부사장", "윤서연 전무"], 60, "2026-11-02", "2026-11-06")
c = r["candidates"]
check("m-04", 1 <= len(c) <= 3 and all("2026-11-02" <= x["start"][:10] <= "2026-11-06" for x in c)
      and not any(x["start"] == "2026-11-03T15:00" for x in c), text(r))
r = T.find_candidates(ctx("sec-kim"), ["강민준 부사장", "오지훈 과장"], 30)
check("m-05", 1 <= len(r["candidates"]) <= 3 and r["duration_min"] == 30, text(r))
r = T.find_candidates(ctx("sec-kim"), ["박정우 대표", "강민준 부사장"], 60)
check("m-06", r["candidates"] and "외부" in r.get("notice", ""), text(r))
r = T.find_candidates(ctx("sec-kim"), ["강민준 부사장", "윤서연 전무"], 60)
c2 = r["candidates"][1]
r = T.register_event(keep("sec-kim"), "임원 회의", c2["start"], c2["end"], ["강민준 부사장", "윤서연 전무"])
check("m-07", r.get("registered_for") == ["exec-kang"] and r.get("pending_approval_for") == ["exec-yoon"], text(r))
r = T.update_event(ctx("exec-kang"), "ev-04", "2026-10-28T11:00", "2026-10-28T12:00")
check("m-08", r.get("applied") and r["pending_approval_for"] == [], text(r))
r = T.cancel_event(ctx("sec-jung"), "ev-04")
check("m-09", r.get("pending_approval_for") == ["exec-kang"] and not r["applied"], text(r))
r = T.mark_absent(ctx("sec-kim"), "ev-07")
check("m-10", r.get("pending_approval_for") == ["exec-kang"], text(r))
r = T.list_pending_approvals(ctx("exec-kang"))
check("m-11", "예산 협의" in text(r), text(r))
r = T.decide_approval(keep("exec-kang"), "ap-01", True)
r2 = T.list_pending_approvals(keep("exec-kang"))
check("m-12", r.get("approved") is True and r2["pending"] == [], text(r) + text(r2))
r = T.get_profile(ctx("sec-kim"), "ABC사 박정우 대표")
check("m-13", r.get("phone") == "010-1234-5678" and r.get("email") == "park@abc.example", text(r))
r = T.register_external_profile(ctx("sec-kim"), "임수빈", "이사", "XYZ사", "010-2222-3333", "lim@xyz.example")
check("m-14", r.get("created") and T.get_profile(keep("sec-kim"), "임수빈")["org"] == "XYZ사", text(r))
r = T.set_assignment(ctx("admin-jo"), "정하은 비서", "한도윤 상무")
check("m-15", r.get("updated") and T.load_requester("sec-jung", DB).executive == "exec-han", text(r))
r = T.list_events(ctx("sec-kim"), "윤서연 전무", "2026-10-29")
check("m-16", r.get("denied") and "승진 심사" not in text(r) and "인사위원회" not in text(r), text(r))
r = T.get_event_at(ctx("sec-kim"), "강민준 부사장", "2026-10-27T14:00")
check("m-17", r.get("denied") and "건강검진" not in text(r), text(r))
r = T.list_events(ctx("admin-jo"), "강민준 부사장", "2026-10-27")
check("m-18", r.get("denied") and "주간 경영회의" not in text(r), text(r))
r = T.update_event(ctx("sec-kim"), "ev-07", "2026-10-30T15:00", "2026-10-30T16:00")
ev = q("SELECT start FROM events WHERE id='ev-07'")
check("m-19", r.get("denied") and r.get("suggestion") == "불참" and ev == "2026-10-30T10:00", text(r))
r = T.get_profile(ctx("sec-kim"), "DEF사 최동혁 대표")
check("m-20", r.get("no_answer"), text(r))
r = T.find_candidates(ctx("sec-choi"), ["한도윤 상무"], 60, "2026-11-02", "2026-11-06")
check("m-21", r.get("no_answer") and r["candidates"] == [], text(r))

# 추가 규칙 확인
r = T.decide_approval(ctx("sec-kim"), "ap-01", True)
check("비서는 참석 요청 대신 승인 가능", r.get("approved") is True, text(r))
T.cancel_event(ctx("sec-jung"), "ev-04")
ap = q("SELECT id FROM approvals WHERE kind='취소'")
r = T.decide_approval(keep("sec-kim"), ap, True)
check("다른 비서는 동료 비서의 취소 승인 불가", r.get("denied"), text(r))
r = T.decide_approval(keep("exec-kang"), ap, True)
gone = q("SELECT COUNT(*) FROM events WHERE id='ev-04'") == 0
check("임원 승인 시 취소 반영", r.get("approved") and gone, text(r))
c = ctx("exec-yoon")
r = T.update_event(c, "ev-07", "2026-10-30T15:00", "2026-10-30T16:00")
ap = q("SELECT id FROM approvals WHERE kind='시간 변경'")
T.decide_approval(keep("exec-kang"), ap, False)
st = q("SELECT status FROM attendees WHERE event_id='ev-07' AND person_id='exec-kang'")
ev = q("SELECT start FROM events WHERE id='ev-07'")
check("주최 시간 변경 거절 시 그 임원만 불참, 새 시간 유지", st == "불참" and ev == "2026-10-30T15:00", f"{st} {ev}")
r = T.register_event(ctx("sec-kim"), "비밀 일정", "2026-11-02T09:00", "2026-11-02T10:00", [], private=True)
check("비서는 비공개 일정 생성 불가", r.get("denied"), text(r))
r = T.find_candidates(ctx("admin-jo"), ["강민준 부사장"])
check("관리자는 조율 불가", r.get("denied"), text(r))
r = T.list_assignments(ctx("sec-kim"))
check("비서는 담당 관계 조회 불가", r.get("denied"), text(r))
r = T.get_profile(ctx("sec-kim"), "강 부사장")
check("성+직책으로는 찾지 않음", r.get("not_found"), text(r))

tools = T.build_tools(ctx("sec-kim"))
check("build_tools 묶음", {k: len(v) for k, v in tools.items()} == {"조율": 3, "일정": 9, "관리": 2})
# RAG: 실제 Bedrock 대신 가짜 임베딩으로 메모리 안에서만 확인합니다(비용·네트워크 없음).
# 실제 임베딩 품질은 이 검사로 알 수 없습니다. 대상 판정과 문서 필터가 맞는지만 봅니다.
from langchain_core.embeddings import DeterministicFakeEmbedding  # noqa: E402
from src import retriever as R  # noqa: E402

store = R.build_vectorstore(DeterministicFakeEmbedding(size=64), persist_dir=None, rebuild=True)
for qid, subject, question, source, must in [
    ("m-22", "ABC사 박정우 대표", "어떤 분이야?", "ext_park_abc.md", "반도체 장비"),
    ("m-23", "한국대학교 고은비 교수", "연구 분야가 뭐야?", "ext_goh_hankuk.md", "배터리"),
    ("조사가 붙은 대상", "ABC사의", "회사 소개", "ext_park_abc.md", "반도체 장비"),
]:
    r = R.search_intro(store, subject, question)
    srcs = {x["source"] for x in r["results"]}
    check(qid, srcs == {source} and any(must in x["content"] for x in r["results"]), text(r))
r = R.search_intro(store, "GHI사 송재원 이사", "최근 소식")
check("m-24", r.get("no_answer") and r["results"] == [], text(r))
check("검색 도구 생성", R.build_search_tool(store).name == "tool_search_intro")

print("\nFAILS:", fails)
sys.exit(1 if fails else 0)

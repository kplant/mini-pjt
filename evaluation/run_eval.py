"""평가셋(evaluation/test_queries.csv)을 실행하고 expect를 코드로 판정합니다.

실행: python evaluation/run_eval.py [--runs 1] [--ids m-01,m-04] [--ragas]
--ragas를 주면 근거 문서가 있는 문항(RAGAS_REFERENCES)의 응답으로 RAGAS 4개 지표도 계산합니다(TASKS 5-2).
문항마다 DB를 초기화하고 새 thread_id로 보냅니다. turns가 있으면 같은 thread_id로 차례로 보내고 마지막 응답으로 판정합니다.
route·refused·후보 시간·승인 대기는 응답 trace의 decision 단계에서, 나머지는 실행 후 DB 상태로 판정합니다
(evaluation/eval-fixtures.md의 '판정 필드').
"""
import argparse
import csv
import json
import os
import sys
import time
import types
import uuid
import warnings
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from src import db  # noqa: E402
from src.agent import decision, run_query  # noqa: E402
from src.tools import LUNCH, WORK_END_HOUR, WORK_START_HOUR, _busy_blocks, resolve_person  # noqa: E402

CSV_PATH = root / "evaluation" / "test_queries.csv"
SEED_PATH = root / "data" / "seed.json"
LIMIT_S = 10  # 요청 하나의 응답 시간 기준(SERVICE.md 5번)

# SERVICE.md 5번 성공 기준
MIN_ACCURACY, MIN_GUARDRAIL, MIN_ROUTING = 22, 4, 18

# RAGAS 대상(근거 문서가 있는 문항: 조회·브리핑, 소개 자료 RAG)과 정답 문장.
# eval-fixtures.md와 data/*.md에 적힌 사실로만 씁니다. context_recall·context_precision이 이 문장을 기준으로 봅니다.
RAGAS_REFERENCES = {
    "m-01": "10월 27일 강민준 부사장의 일정은 09:00~10:00 주간 경영회의, 14:00~15:00 바쁨(비공개 일정), "
            "16:00~17:00 ABC사 미팅이다.",
    "m-02": "10월 27일 강민준 부사장의 일정은 09:00~10:00 주간 경영회의, 14:00~15:00 건강검진, "
            "16:00~17:00 ABC사 미팅이다.",
    "m-03": "10월 29일(목) 윤서연 전무의 일정은 10:00~11:00 인사위원회, 14:00~15:00 바쁨(비공개 일정)이다.",
    "m-22": "ABC사는 반도체 장비 제조사이고, 박정우 대표는 반도체 장비 업계에서 25년간 일했으며 "
            "2019년에 ABC사 대표로 취임했다.",
    "m-23": "고은비 교수의 연구 분야는 배터리 소재, 특히 전고체 배터리의 고체 전해질이다.",
}
# ragas 결과 키 → TASKS의 지표 이름
RAGAS_METRICS = {
    "context_recall": "context_recall",
    "llm_context_precision_with_reference": "context_precision",
    "faithfulness": "faithfulness",
    "answer_relevancy": "answer_relevancy",
}


def load_cases(ids: list[str] | None = None) -> list[dict]:
    """CSV에서 문항을 읽습니다. ids가 있으면 그 문항만 돌려줍니다."""
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        cases = list(csv.DictReader(f))
    for c in cases:
        c["expect"] = json.loads(c["expect"]) if c["expect"] else {}
        c["turns"] = json.loads(c["turns"]) if c["turns"] else [c["question"]]
    return [c for c in cases if not ids or c["id"] in ids]


def run_case(case: dict) -> dict:
    """DB를 초기화하고 문항을 실행합니다. 반환: {"response", "latencies", "error"}"""
    db.reset_db()
    thread_id = str(uuid.uuid4())
    response, latencies = None, []
    try:
        for q in case["turns"]:
            start = time.time()
            response = run_query(q, case["user_id"], case["base_date"], thread_id=thread_id)
            latencies.append(round(time.time() - start, 2))
        return {"response": response, "latencies": latencies, "error": ""}
    except Exception as exc:  # noqa: BLE001 - 한 문항의 오류로 평가 전체를 멈추지 않습니다
        return {"response": response, "latencies": latencies, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}


def _rows(sql: str, *args) -> list[tuple]:
    """평가용 DB 조회."""
    conn = db.connect()
    try:
        return [tuple(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def check_candidates(cands: list[dict], spec: dict, attendees: list[str]) -> list[str]:
    """후보 시간의 개수·길이·기간·근무 시간·바쁨 겹침을 확인합니다. 바쁨은 초기 상태의 DB로 봅니다."""
    fails = []
    if not spec.get("min", 0) <= len(cands) <= spec.get("max", 99):
        fails.append(f"후보 {len(cands)}개(기대 {spec.get('min')}~{spec.get('max')})")
    db.reset_db()
    conn = db.connect()
    try:
        people = [p for name in attendees for p in resolve_person(conn, name)[:1] if p["role"] != "외부 인물"]
        blocks = [(s, e) for p in people for s, e, _ in _busy_blocks(conn, p["id"])]
    finally:
        conn.close()
    for c in cands:
        s, e = datetime.fromisoformat(c["start"]), datetime.fromisoformat(c["end"])
        if "duration_min" in spec and (e - s).total_seconds() / 60 != spec["duration_min"]:
            fails.append(f"길이 {c['start']}")
        if "from" in spec and not spec["from"] <= c["start"][:10] <= spec["to"]:
            fails.append(f"기간 밖 {c['start']}")
        lunch = (s.replace(hour=LUNCH[0], minute=0), s.replace(hour=LUNCH[1], minute=0))
        if s.hour < WORK_START_HOUR or e > s.replace(hour=WORK_END_HOUR, minute=0) or (s < lunch[1] and e > lunch[0]):
            fails.append(f"근무 시간 밖 {c['start']}")
        if any(s < be and e > bs for bs, be in blocks):
            fails.append(f"바쁨과 겹침 {c['start']}")
    return fails


def _seed_event(title: str) -> dict | None:
    """data/seed.json에서 제목으로 일정을 찾습니다."""
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return next((e for e in seed["events"] if e["title"] == title), None)


def judge_case(case: dict, run: dict) -> list[str]:
    """실행 결과를 expect와 비교해 실패 이유 목록을 돌려줍니다. 비어 있으면 PASS입니다.

    DB 상태 검사는 실행 직후의 DB를 읽으므로 run_case 바로 뒤에 불러야 합니다.
    """
    if run["error"]:
        return [f"오류 {run['error']}"]
    resp, exp = run["response"], case["expect"]
    d, answer = decision(resp["trace"]), resp["answer"]
    fails = []
    if case["expected_route"] and d.get("route") != case["expected_route"]:
        fails.append(f"route={d.get('route')}(기대 {case['expected_route']})")
    for key in ("refused", "no_answer"):
        if key in exp and bool(d.get(key)) != exp[key]:
            fails.append(f"{key}={d.get(key)}")
    fails += [f"'{m}' 없음" for m in exp.get("must_include", []) if m not in answer]
    fails += [f"'{m}' 있음" for m in exp.get("must_not_include", []) if m in answer]
    if "registered_for" in exp and d.get("registered_for") != exp["registered_for"]:
        fails.append(f"registered_for={d.get('registered_for')}")
    if "pending_approval_for" in exp and d.get("pending_approvals") != exp["pending_approval_for"]:
        fails.append(f"pending_approval_for={d.get('pending_approvals')}")
    for title in exp.get("approved", []):
        statuses = [s for (s,) in _rows("SELECT ap.status FROM approvals ap JOIN events e ON e.id = ap.event_id "
                                         "WHERE e.title = ?", title)]
        if "승인" not in statuses:
            fails.append(f"'{title}' 승인 안 됨")
    if "profile_created" in exp:
        p = exp["profile_created"]
        if not _rows("SELECT id FROM people WHERE name = ? AND org = ?", p["name"], p["org"]):
            fails.append(f"프로필 {p['name']}({p['org']}) 없음")
    if "assignment" in exp:
        a = exp["assignment"]
        if _rows("SELECT executive FROM assignments WHERE secretary = ?", a["secretary"]) != [(a["executive"],)]:
            fails.append(f"담당 관계 {a['secretary']} → {a['executive']} 아님")
    if "unchanged_event" in exp:
        seed = _seed_event(exp["unchanged_event"])
        now = _rows("SELECT start, end FROM events WHERE title = ?", exp["unchanged_event"])
        if not seed or now != [(seed["start"], seed["end"])]:
            fails.append(f"'{exp['unchanged_event']}' 바뀜 {now}")
    if case["expected_source"] and case["expected_source"] not in [c["doc_id"] for c in resp["contexts"]]:
        fails.append(f"contexts에 {case['expected_source']} 없음")
    if "candidates" in exp:  # DB를 다시 초기화하므로 DB 검사 뒤에 둡니다
        steps = [s["output"] for s in resp["trace"] if s["step"].endswith("tool_find_candidates")]
        attendees = steps[-1].get("attendees", []) if steps else []
        fails += check_candidates(d.get("candidates", []), exp["candidates"], attendees)
    return fails


def evaluate(cases: list[dict]) -> list[dict]:
    """문항을 차례로 실행하고 판정합니다. 진행 상황을 한 줄씩 출력합니다."""
    results = []
    for case in cases:
        run = run_case(case)
        fails = judge_case(case, run)
        resp = run["response"] or {}
        d = decision(resp["trace"]) if resp else {}
        results.append({"id": case["id"], "type": case["type"], "route": d.get("route"),
                        "expected_route": case["expected_route"], "turns": len(case["turns"]),
                        "latencies": run["latencies"], "fails": fails, "question": case["turns"][-1],
                        "answer": resp.get("answer", ""), "contexts": [c["text"] for c in resp.get("contexts", [])]})
        print(f"  {case['id']} {'PASS' if not fails else 'FAIL'} {run['latencies']}", flush=True)
    db.reset_db()
    return results


def summarize(results: list[dict]) -> dict:
    """SERVICE.md 5번 기준으로 한 회차를 요약합니다."""
    passed = [r for r in results if not r["fails"]]
    guard = [r for r in results if r["type"] == "guardrail"]
    routed = [r for r in results if r["expected_route"]]
    latencies = [t for r in results for t in r["latencies"]]
    m07 = next((r for r in results if r["id"] == "m-07"), None)
    return {
        "정답률": (len(passed), len(results)),
        "권한": (sum(not r["fails"] for r in guard), len(guard)),
        "라우팅": (sum(r["route"] == r["expected_route"] for r in routed), len(routed)),
        "10초 초과": (sum(t > LIMIT_S for t in latencies), len(latencies)),
        "조율 효율(m-07)": None if m07 is None else (not m07["fails"] and m07["turns"] <= 2),
    }


def meets(s: dict) -> dict:
    """요약이 기준을 넘는지 항목별로 돌려줍니다. 문항 일부만 돌렸으면 개수 기준 대신 전부 통과를 봅니다."""
    full = s["정답률"][1] == 24
    return {
        "정답률": s["정답률"][0] >= MIN_ACCURACY if full else s["정답률"][0] == s["정답률"][1],
        "권한": s["권한"][0] == s["권한"][1],
        "라우팅": s["라우팅"][0] >= MIN_ROUTING if full else s["라우팅"][0] == s["라우팅"][1],
        "10초 초과": s["10초 초과"][0] == 0,
        "조율 효율(m-07)": s["조율 효율(m-07)"] is not False,
    }


def _import_ragas():
    """ragas를 import합니다.

    ragas 0.4.3은 langchain-community 0.4에서 빠진 chat_models.vertexai를 import하므로 빈 모듈로 채웁니다
    (Vertex AI는 쓰지 않습니다). 사용 통계 전송은 끄고, 사용 중단 예고 경고는 숨깁니다.
    Python 3.14에서는 scikit-network(평가셋 생성 기능에만 쓰임)가 빌드되지 않아 ragas를 --no-deps로 설치합니다(README).
    """
    os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
    name = "langchain_community.chat_models.vertexai"
    if name not in sys.modules:
        stub = types.ModuleType(name)
        stub.ChatVertexAI = type("ChatVertexAI", (), {})
        sys.modules[name] = stub
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import ragas

    return ragas


def ragas_scores(results: list[dict]) -> dict:
    """RAGAS 대상 문항의 응답으로 4개 지표를 계산합니다. 반환: {"mean": {지표: 값}, "per_case": {id: {지표: 값}}}

    평가 모델은 Agent와 같은 첫 후보(Sonnet), 임베딩은 Titan입니다. 질문을 다시 보내지 않고 받은 응답을 그대로 씁니다.
    """
    _import_ragas()
    from ragas import EvaluationDataset, evaluate as ragas_evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall, ResponseRelevancy
    from src.agent import make_model, model_ids
    from src.retriever import _default_embeddings

    targets = [r for r in results if r["id"] in RAGAS_REFERENCES]
    if not targets:
        return {"mean": {}, "per_case": {}}
    dataset = EvaluationDataset.from_list([{
        "user_input": r["question"], "response": r["answer"],
        "retrieved_contexts": r["contexts"] or [""], "reference": RAGAS_REFERENCES[r["id"]],
    } for r in targets])
    scored = ragas_evaluate(
        dataset,
        metrics=[LLMContextRecall(), LLMContextPrecisionWithReference(), Faithfulness(), ResponseRelevancy()],
        llm=LangchainLLMWrapper(make_model(model_ids()[0])),
        embeddings=LangchainEmbeddingsWrapper(_default_embeddings()),
        show_progress=False,
    )
    per_case = {r["id"]: {RAGAS_METRICS[k]: round(float(v), 3) for k, v in row.items() if k in RAGAS_METRICS}
                for r, row in zip(targets, scored.scores)}
    mean = {name: round(sum(c[name] for c in per_case.values()) / len(per_case), 3) for name in RAGAS_METRICS.values()}
    return {"mean": mean, "per_case": per_case}


def print_ragas(all_scores: list[dict]) -> None:
    """RAGAS 지표를 회차별 평균 표와 문항별 표로 출력합니다."""
    print("\n| RAGAS 지표 | " + " | ".join(f"{i + 1}회" for i in range(len(all_scores))) + " |")
    print("|---" * (len(all_scores) + 1) + "|")
    for name in RAGAS_METRICS.values():
        print(f"| {name} | " + " | ".join(str(s["mean"].get(name, "-")) for s in all_scores) + " |")
    print("\n| 문항(마지막 회차) | " + " | ".join(RAGAS_METRICS.values()) + " |")
    print("|---" * (len(RAGAS_METRICS) + 1) + "|")
    for cid, row in all_scores[-1]["per_case"].items():
        print(f"| {cid} | " + " | ".join(str(row[n]) for n in RAGAS_METRICS.values()) + " |")


def print_table(results: list[dict]) -> None:
    """문항별 PASS/FAIL 표를 출력합니다."""
    print(f"| {'id':<5} | {'type':<12} | 결과 | {'route':<4} | 최대 응답(초) | 실패 이유")
    print("|-------|--------------|------|------|---------------|----------")
    for r in results:
        worst = max(r["latencies"]) if r["latencies"] else 0
        print(f"| {r['id']:<5} | {r['type']:<12} | {'PASS' if not r['fails'] else 'FAIL'} | {str(r['route']):<4} "
              f"| {worst:>13} | {'; '.join(r['fails'])}")


def print_summary(summaries: list[dict]) -> None:
    """회차별 요약과 기준 통과 여부를 나란히 출력합니다."""
    def cell(v) -> str:
        return f"{v[0]}/{v[1]}" if isinstance(v, tuple) else ("-" if v is None else ("통과" if v else "미달"))

    print("\n| 기준 | " + " | ".join(f"{i + 1}회" for i in range(len(summaries))) + " | 모든 회차 기준 통과 |")
    print("|---" * (len(summaries) + 2) + "|")
    for key in summaries[0]:
        ok = all(meets(s)[key] for s in summaries)
        print(f"| {key} | " + " | ".join(cell(s[key]) for s in summaries) + f" | {'통과' if ok else '미달'} |")


def main() -> None:
    """명령줄 인자를 읽어 평가를 실행합니다."""
    parser = argparse.ArgumentParser(description="평가셋 실행과 판정")
    parser.add_argument("--runs", type=int, default=1, help="전체 실행 횟수")
    parser.add_argument("--ids", default="", help="쉼표로 구분한 문항 id(비우면 전체)")
    parser.add_argument("--ragas", action="store_true", help="RAGAS 4개 지표도 계산(근거 문서가 있는 문항)")
    args = parser.parse_args()
    cases = load_cases([i.strip() for i in args.ids.split(",") if i.strip()])
    summaries, all_scores = [], []
    for n in range(args.runs):
        print(f"\n## {n + 1}회차 ({len(cases)}문항)", flush=True)
        results = evaluate(cases)
        print()
        print_table(results)
        summaries.append(summarize(results))
        if args.ragas:
            start = time.time()
            all_scores.append(ragas_scores(results))
            print(f"\n(RAGAS 계산 {time.time() - start:.1f}초)", flush=True)
    print_summary(summaries)
    if all_scores:
        print_ragas(all_scores)


if __name__ == "__main__":
    main()

# 계획: TASKS 3-5 관리 Agent + Supervisor 모델 원복(Sonnet)

## Context
- 사용자가 Sonnet 한도를 초기화했고, Supervisor 모델을 Haiku에서 Sonnet으로 되돌리기로 결정(2026-10-22). Haiku로 바꾼 이유는 응답 시간(3-1 m-04 13.64초, 모두 Sonnet 4.5)이었으므로 10초 초과가 다시 늘 수 있음을 감안한 결정
- `.env`의 `SUPERVISOR_MODEL_ID`로 1순위만 바꿀 수 있는 장치는 남김(사용자 결정)
- 3-5 확인 항목: m-15(admin-jo, "정하은 비서를 한도윤 상무 담당으로 바꿔줘") 실행 후 sec-jung의 담당 임원이 exec-han
- 도구는 이미 있음: `list_assignments`·`set_assignment`(관리자만). check_tools.py가 m-15 검사

## 변경 파일
A. Supervisor 모델 원복
- `src/agent.py`: `SUPERVISOR_MODEL_ID` 상수 삭제. `supervisor_model_ids()`는 기본 `model_ids()`, `.env`의 `SUPERVISOR_MODEL_ID`가 있으면 그 모델을 맨 앞에
- `CLAUDE.md` 33행, `README.md` 15행: "Supervisor도 같은 후보 순서, `.env`의 `SUPERVISOR_MODEL_ID`로 1순위만 바꿀 수 있음"

B. 관리 Agent
- `src/agent.py`
  - `ADMIN_PROMPT`: 조회는 tool_list_assignments, 변경은 tool_set_assignment(성명 전체), 분명하면 되묻지 않음, denied·not_found면 reason 전달
  - `build_admin_agent`: `_build_sub_agent(ctx, ADMIN_PROMPT, build_tools(ctx)["관리"], ...)`
  - `SUB_AGENTS`에 `admin_agent: 관리`
  - `SUPERVISOR_PROMPT`: "담당 관계 조회·변경은 admin_agent", "일정·사람 요청은 요청자가 관리자여도 schedule_agent(권한은 도구가 판단)"
  - 모듈 docstring 구현 범위
- `README.md` 구현 범위 3-5까지
- `TASKS.md` 3-5에 "+ Supervisor 모델 원복(Sonnet)", 확인에 "전체 문항 route 유지" 추가, 통과 후 `[x]`

## 검증
1. m-15 3회: route=관리, refused=false, DB assignments sec-jung → exec-han
2. Supervisor가 실제로 Sonnet 4.5로 답했는지 검증 스크립트에서 출력
3. 전체 회귀 1회(응답 시간 기록): m-01~m-14·m-20·m-22~m-24 route=일정 + 기존 기준(DB 포함), m-04~m-07·m-21 route=조율
4. 가드레일 관찰(합격 기준 아님, 4-1): m-16~m-19의 refused·route 기록, 특히 m-18이 일정 Agent로 가는지
5. check_tools.py 37개 PASS
6. 커밋 `TASKS 3-5: 관리 Agent, Supervisor Sonnet 원복`

## 위험
- 응답 시간 10초 초과 증가 → 수치 기록해 5-5로
- m-18이 관리 Agent로 가면 Supervisor 규칙 보강 후 결과에 기록

## 결과(2026-10-22)
- m-15 3회: 3/3 PASS(route=관리, tool_set_assignment, DB sec-jung → exec-han), 11.39·6.43·6.16초
- Supervisor 모델: 모든 실행에서 global Sonnet 4.5로 답함(하위 Agent도 같음, 모델 대체 없음)
- 전체 회귀 1회: m-01~m-14·m-20~m-24·m-07 20건 모두 PASS(route, must_include / must_not_include, no_answer, 후보, 승인 대기, contexts, DB 상태)
- 가드레일 관찰(4-1 범위, 합격 기준 아님): m-16~m-19 모두 route=일정, refused와 must_include / must_not_include가 기대와 같음. m-18(관리자의 일정 요청)도 일정 Agent로 가서 도구가 "관리자는 일정을 볼 수 없습니다"로 거절
- 응답 시간(Sonnet Supervisor): 24건 중 10초 초과 4건 — m-08 14.28초, m-19 11.7초, m-15 11.39초(1회차), m-22 10.08초. 나머지 6.2~9.8초. 3-1 때(m-04 13.64초)보다 m-04는 8.03초로 줄었음
- check_tools.py 37개 PASS
- 계획과 달라진 점: 없음

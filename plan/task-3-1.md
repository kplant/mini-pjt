# 계획: TASKS 3-1 Supervisor 아래에 조율 Agent 연결

## Context
ADR 0003: Supervisor도 `create_agent`로 만들고, 하위 Agent(조율·일정·관리)는 도구로 감싸 넘긴다. 어느 하위 Agent 도구를 불렀는지가 decision 단계의 `route`가 된다. 권한은 도구 계층이 검사한다.
지금 `run_query`는 조율 Agent를 바로 부르고 `route="조율"`을 코드에 고정한다. 3-1에서 Supervisor가 고른 결과로 바꾼다. 일정·관리 Agent는 3-2~3-5에서 붙인다.

## 설계 결정 (2026-10-22 사용자 승인)
1. 하위 Agent에는 사용자 원래 질문을 그대로 넘긴다. Supervisor는 고르기만 하고 바꿔 쓰지 않는다(도구 인자 없음, 원래 질문은 코드가 전달).
2. 하위 Agent 도구는 `return_direct=True`. Supervisor가 답을 다시 쓰지 않아 늘어나는 모델 호출은 라우팅 1회뿐이다.
3. 대화 기억은 Supervisor(`user:thread`)와 조율 Agent(`user:thread:조율`) 각각에 둔다.

## 변경 파일
1. `src/agent.py` (바뀐 부분만)
   - `SUPERVISOR_PROMPT`: 하위 Agent 설명, 반드시 하나를 고르고 직접 답하지 않음. 해당 도구가 없으면 지원하지 않는다고 짧게 답함
   - `SUB_AGENTS = {"coordination_agent": "조율"}`: Bedrock 도구 이름은 영문만 되므로 route 이름과 분리
   - `build_supervisor(...)`: 조율 Agent를 감싼 도구(원래 질문으로 실행, 도구 호출·답한 모델을 sink에 모음, `ensure_notices` 적용 답 반환). Supervisor에도 모델 대체 적용
   - `run_query`: Supervisor 실행. route는 sink의 하위 Agent route(없으면 None). 답변은 하위 Agent 답(없으면 Supervisor 답). trace는 route → 조율.tool_* → decision. 모르는 user_id 거절 경로 그대로
2. `README.md`: Supervisor "구현 예정" 표시가 있으면 갱신
3. `TASKS.md` 3-1 `[x]`, 이 파일 끝에 결과

## 검증
1. m-04: `route="조율"`, 후보가 2-3 때와 같음, 단계 route → 조율.tool_find_candidates → decision, 응답 시간 기록
2. m-05·m-06·m-21 2-2 기준 통과, `route="조율"`
3. m-07 두 턴: 2턴도 `route="조율"`, registered_for=[exec-kang], pending=[exec-yoon]
4. 범위 밖(m-01): `route=None`, 오류 없음
5. `check_tools.py` 35개 PASS
6. 커밋 `TASKS 3-1: Supervisor`

## 위험
- 라우팅 호출 1회로 1~3초 늘어남. 10초를 넘으면 보고하고, Supervisor만 Haiku 1순위로 쓰는 안은 5-5에서 사용자 결정으로 넘긴다.
- Sonnet 일일 한도가 다시 차면 대체 모델로 시간이 늘 수 있으며, 그 경우 원인을 구분해 보고한다.

## 결과(2026-10-22)
- m-04: route=조율, 단계 route → 조율.tool_find_candidates → decision, 후보 11-02·03·04 09:00~10:00(2-3 때와 같음), 13.64초
- m-05(30분 후보 3개, 9.07초), m-06(후보 3개 + 외부 안내, 7.92초), m-21(no_answer=true, 후보 0개, 9.8초) 모두 route=조율
- m-07: 1턴 route=조율 후보 3개(10.51초), 2턴 route=조율 registered_for=[exec-kang], pending=[exec-yoon](10.43초). Supervisor·조율 Agent 각각의 대화 기억으로 "2번으로 해줘"가 조율로 감
- m-01(범위 밖): 하위 Agent를 부르지 않고 route=None, "일정 브리핑 기능은 아직 지원하지 않는 요청입니다"(2.26초)
- check_tools.py 35개 PASS
- 구현 메모: 모델·대체 미들웨어 구성을 `_model_setup()`으로 묶어 조율 Agent와 Supervisor가 함께 씀. 하위 Agent 도구는 `StructuredTool.from_function(..., return_direct=True)`, 인자 없음
- 계획과 달라진 점: 없음
- 미달(5-5로 넘김): 라우팅 호출이 늘어 m-04 13.64초, m-07 두 턴 약 10.5초로 10초 기준을 넘음. 모든 실행이 global Sonnet 4.5로 처리되어 모델 대체 때문은 아님. 대책 후보: Supervisor만 Haiku 1순위(사용자 결정 필요)

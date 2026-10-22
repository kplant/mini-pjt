# 계획: TASKS 1-2 조율 Agent 하나 (m-04 한 경로)

## Context
최소 경로의 두 번째 단계다. 질문 하나를 받아 조율 Agent가 도구로 후보 시간을 찾고, 답변 문장을 돌려주는 데까지 만든다. 응답 형식(answer/contexts/trace)은 1-3, HTTP 서버는 1-4, 모델 자동 전환은 2-3에서 한다. 이번에는 `model_ids()`의 첫 모델 하나만 쓴다(지금은 `.env`에 따라 global Sonnet 4.5).

확인 기준(TASKS 1-2): m-04 질문(`sec-kim`, 기준일 2026-10-26)의 답변에 11-02~11-06 사이 후보 시간 1~3개가 나온다.

## 바꿀 파일: `src/agent.py`에 덧붙이기
기존 모델 부분은 그대로 두고 아래만 추가한다.

1. **`date_hints(base_date) -> str`**: 상대 날짜를 코드로 미리 계산해 프롬프트에 넣는다(계산은 LLM이 아니라 코드로).
   - 기준일과 요일, 내일, 이번 주(월~금), 다음 주(월~금)를 `YYYY-MM-DD`로 적는다.
2. **`requester_desc(ctx) -> str`**: 요청자의 성명, 역할, 담당 임원의 성명과 직책을 DB에서 읽어 한 줄로 만든다.
3. **`COORDINATION_PROMPT`**(조율 Agent 지시문). 안내만 하고 판정은 도구가 한다.
   - 사람은 성명 전체로 도구에 넘긴다. 날짜는 날짜 안내의 값을 그대로 쓴다.
   - 후보 시간은 `tool_find_candidates` 결과를 번호와 함께 그대로 전하고, 직접 만들지 않는다.
   - 도구 결과에 `denied`, `no_answer`, `conflict`, `notice`가 있으면 그 이유나 안내를 그대로 전한다.
   - 회의 길이를 말하지 않으면 도구의 기본값을 쓴다. 등록은 사용자가 후보를 고른 뒤에만 한다.
   - 한국어로 짧게 답한다.
4. **`build_coordination_agent(ctx, llm=None)`**: `create_agent(model=llm or make_model(model_ids()[0]), tools=build_tools(ctx)["조율"], system_prompt=...)`.
5. **`run_query(question, user_id="sec-kim", base_date=None, llm=None, db_path=DEFAULT_DB) -> str`**
   - `base_date`는 `"YYYY-MM-DD"` 문자열이나 `date`를 받는다. 없으면 오늘 날짜.
   - `tools.load_requester`로 요청자를 찾는다. 없으면 LLM을 부르지 않고 "등록되지 않은 사용자입니다"를 돌려준다(정식 처리는 4-1).
   - 마지막 AI 메시지의 텍스트를 `get_text`로 돌려준다.
   - 메시지 목록을 꺼내는 부분은 별도 함수 `_invoke(agent, question)`로 둔다(1-3에서 dict 반환으로 바꿈).

## 재사용
- `src/tools.py`: `Ctx`, `load_requester`, `build_tools(ctx)["조율"]`
- `src/db.py`: `DEFAULT_DB`, `connect`, `reset_db`
- `src/agent.py`: `model_ids`, `make_model`, `get_text`
- 참고만: `sds-ax-practice/day5_practice/day5_final.py`의 `create_agent` 호출 방식

## 검증
1. 실제 DB를 `reset_db()`로 초기화한 뒤 일회성 명령으로 m-04를 실행한다(새 파일 없음).
   - `run_query("다음 주에 강민준 부사장님과 윤서연 전무님 1시간 회의 잡아줘", "sec-kim", "2026-10-26")`
   - 출력: 답변 문장, 도구 호출 인자, 도구 결과의 후보 시간, 걸린 시간
   - 통과 조건: 도구가 `date_from=2026-11-02`, `date_to=2026-11-06`으로 불렸고, 답변에 그 결과의 후보 1~3개가 그대로 나오며, 11-03 15:00은 나오지 않는다.
2. 모르는 `user_id`("nobody")로 부르면 LLM 호출 없이 안내 문구가 나온다.
3. `python evaluation/check_tools.py`가 35개 모두 통과한다.
4. 통과하면 `TASKS.md`의 1-2를 `[x]`로 바꾸고 `TASKS 1-2: 조율 Agent`로 커밋한다(`plan/` 포함).

## 결과(2026-10-22)
- 모델: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`(`.env` 순서의 첫 번째)
- 도구 호출: `tool_find_candidates(attendees=["강민준 부사장", "윤서연 전무"], date_from="2026-11-02", date_to="2026-11-06", duration_min=60)`
- 도구 결과와 답변이 일치: 11-02(월), 11-03(화), 11-04(수) 각각 09:00~10:00. 11-03 15:00은 나오지 않음
- 걸린 시간: **8.2초**. Agent 하나로도 10초 기준에 가깝다. Supervisor를 더하는 3-1에서 다시 재고, 5-4에서 대응한다.
- 모르는 `user_id`("nobody"): LLM을 부르지 않고 안내 문구를 돌려줌
- 회귀: `check_tools.py` 35개 통과
- 달라진 점: `agent.py`가 `src.tools`를 import하므로 모델 확인은 `python -m src.agent`로 실행한다(task-1-1.md에 반영).

# 계획: TASKS 1-3 응답 형식(answer / contexts / trace)

## Context
`run_query()`는 지금 답변 문장만 돌려준다. 제출 규약은 응답을 `answer`, `contexts`, `trace` 세 키로 돌려달라고 하고, 평가셋은 `trace` 안의 값(route, refused, candidates, 승인 대기 등)으로 판정한다. 이번 작업에서 이 형식을 만든다. 거절 판정의 세부 규칙은 4-1, 연락처 마스킹은 4-2, Supervisor의 라우팅은 3-1에서 다룬다.

확인 기준(TASKS 1-3): m-04 결과의 `trace.candidates`가 `find_candidates` 결과와 같고, 키가 정확히 세 개다.

## 0. 먼저 할 일(사용자 요청)
- `plan/task-1-3.md`에 이 계획을 저장한다.
- 메모리에 "테스트 호출을 할 때는 명령과 출력을 그대로 보여 준다"를 저장한다.

## 바꿀 파일: `src/agent.py`
1. **`collect_tool_calls(messages, agent_name) -> list[dict]`**
   - AI 메시지의 `tool_calls`를 `tool_call_id`로 ToolMessage와 짝지어 `{agent, tool, args, result}`로 만든다. `result`는 도구가 돌려준 JSON을 파싱한 dict다.
   - 파싱에 실패하면 `{"raw": 원문}`으로 남긴다.
2. **`build_trace(calls, route, model_id, latency_s) -> dict`**: 모델이 아니라 도구 결과만으로 정하는 순수 함수다.
   - `route`: 지금은 `"조율"` 고정. 3-1에서 Supervisor가 정한다.
   - `refused`: `denied`인 결과가 하나라도 있으면 참
   - `no_answer`: `no_answer`인 결과가 하나라도 있으면 참
   - `candidates`: 마지막 `tool_find_candidates` 결과의 `candidates`. 호출이 없으면 `[]`
   - `registered_for`, `pending_approvals`: 결과의 `registered_for`, `pending_approval_for`를 순서를 지켜 중복 없이 모은 목록
   - `tool_calls`: 위 목록 그대로(마스킹은 4-2)
   - `model`, `latency_s`
3. **`build_contexts(calls) -> list[dict]`**: 답변의 근거가 된 도구 결과를 `{"source": 도구 이름, "content": 결과 JSON 문자열}`로 담는다. 3-4에서 소개 자료가 들어오면 `source`가 문서 파일명이 된다.
4. **`run_query()`의 반환값을 `{"answer", "contexts", "trace"}`로 바꾼다.**
   - 걸린 시간을 재고, 쓴 모델 ID(`model_ids()[0]`, `llm`을 넣었으면 `"injected"`)를 기록한다.
   - 모르는 `user_id`일 때도 같은 형식으로 돌려준다: `answer`는 안내 문구, `contexts`는 `[]`, `trace`는 `refused=True`, `route=None`, `model=None`.
   - 결과 dict를 만드는 곳은 `_result(answer, contexts, trace)` 하나로 모아, 세 키 말고는 들어가지 않게 한다.

## 재사용
- `src/agent.py`: `_invoke`, `get_text`, `model_ids`, `build_coordination_agent`(1-2에서 만든 것)
- 도구 결과 키(`denied`, `no_answer`, `candidates`, `registered_for`, `pending_approval_for`)는 `src/tools.py`의 형식을 그대로 쓴다.

## 검증(명령과 출력을 그대로 보여 준다)
1. **LLM 없이 `build_trace` 확인**(일회성 명령): `AIMessage`(tool_calls 포함)와 `ToolMessage`를 직접 만들어 넣는다.
   - `denied`가 섞이면 `refused=True`가 되는지
   - 마지막 후보 결과가 `candidates`가 되는지
   - `pending_approval_for`가 모이는지
2. **실제 Bedrock으로 m-04**: `reset_db()` 후 `run_query(m-04, "sec-kim", "2026-10-26")`
   - 결과 JSON 전체를 출력한다.
   - 통과 조건: 키가 정확히 `answer`, `contexts`, `trace`이고, `trace.candidates`가 `trace.tool_calls`의 `find_candidates` 결과와 같으며, `route="조율"`, `refused=False`
3. 모르는 사용자 `nobody` → 같은 세 키, `refused=True`, LLM 호출 없음
4. `python evaluation/check_tools.py` 35개 통과
5. 통과하면 `plan/task-1-3.md`에 결과를 덧붙이고, `TASKS.md` 1-3을 `[x]`로 표시한 뒤 `TASKS 1-3: 응답 형식`으로 커밋한다.

## 결과(2026-10-22)
- `build_trace`를 LLM 없이 확인: `denied`가 섞이면 `refused=True`, 마지막 후보 결과가 `candidates`가 됨, `pending_approval_for`는 중복 없이 모임, 짝이 없는 ToolMessage는 무시함
- 실제 Bedrock m-04(`global` Sonnet 4.5): 키는 정확히 `answer`, `contexts`, `trace`. `trace.candidates`가 도구 결과와 같음, `route="조율"`, `refused=False`, 8.0초
- 모르는 사용자 `nobody`: 같은 세 키, `refused=True`, `model=None`(LLM 호출 없음)
- 회귀: `check_tools.py` 35개 통과

# 계획: TASKS 2-1 대화 기억 (`SqliteSaver` + `thread_id`)

## Context
`run_query`는 질문마다 새 Agent를 만들어 이전 대화를 모릅니다. m-07 2턴 "2번으로 해줘"를 처리하려면 같은 대화의 1턴 후보 목록을 기억해야 합니다. `src/app.py`는 `thread_id`를 받기만 하고 쓰지 않습니다(1-5에서 2-1로 미룸). `langgraph-checkpoint-sqlite` 3.1.2는 requirements·.venv에 이미 있어 새 라이브러리는 없습니다. ADR 0002대로 승인은 대화 기억이 아니라 DB로 다루며, 체크포인트는 같은 요청자의 대화 이어 가기에만 씁니다.

사용자 결정(2026-10-22 승인): 대화 키는 `user_id:thread_id`, `thread_id`가 없으면 기억 없이 처리.

## 변경 파일
1. **`src/agent.py`** (바뀐 부분만)
   - `CHECKPOINT_DB = ROOT / "checkpoints.sqlite"` (`src.db.ROOT` 재사용)
   - `_checkpointer()`: 처음 부를 때 `sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)`로 `SqliteSaver`를 만들어 모듈 변수에 재사용(FastAPI 스레드풀 대비). import 시 만들지 않음.
   - `build_coordination_agent(ctx, llm=None, checkpointer=None)`: `create_agent(..., checkpointer=checkpointer)`. 시스템 프롬프트는 상태에 저장되지 않으므로 매 턴 새로 만들어도 됨.
   - `COORDINATION_PROMPT`에 규칙 1줄: 사용자가 번호로 후보를 고르면 직전 `tool_find_candidates` 결과의 그 번호 start·end와 참석자로 `tool_register_event`를 호출.
   - `_invoke(agent, question, config=None)`: 결과 메시지 중 마지막 사람 메시지 이후만 반환(이전 턴 도구 호출이 trace·`judge`에 중복되지 않게).
   - `run_query(question, user_id, base_date=None, thread_id=None, llm=None, db_path=...)`: `thread_id`가 있으면 체크포인트를 켜고 `{"configurable": {"thread_id": f"{user_id}:{thread_id}"}}`로 실행, 없으면 지금처럼. 모르는 `user_id` 거절 경로는 그대로(LLM·체크포인트 안 씀). docstring 갱신.
2. **`src/app.py`**: `run_query(req.question, req.user_id, req.base_date, thread_id=req.thread_id)`, `QueryRequest` docstring의 "받기만 하고 쓰지 않습니다" 수정.
3. **`.gitignore`**: `checkpoints.sqlite*` 추가.
4. **`README.md`** 53행: `thread_id` 설명을 "같은 `user_id`·`thread_id`로 보내면 이전 대화를 이어 간다(`checkpoints.sqlite`)"로.
5. **`TASKS.md`** 2-1 `[x]`, **`plan/task-2-1.md`**에 이 계획 저장 후 끝에 결과 추가.

## 재사용
`src/db.py`의 `ROOT`·`reset_db`, `src/agent.py`의 `collect_tool_calls`·`judge`·`build_trace`·`decision`·`get_text`, `src/tools.py`의 `register_event`(이미 `registered_for`·`pending_approval_for` 반환).

## 검증 (명령·출력 원문·읽는 법·PowerShell 재현 명령 함께 보고)
1. m-07 함수 호출: `reset_db()` → 새 uuid `thread_id`, `sec-kim`, 기준일 2026-10-26으로 두 턴.
   - 1턴 decision: `candidates` 1~3개, `registered_for=[]`
   - 2턴 decision: `registered_for=["exec-kang"]`, `pending_approvals=["exec-yoon"]`, `refused=false`, 등록 시각 = 1턴 후보 2번. 2턴 trace에 1턴 단계 없음.
   - DB: 새 일정 1건, `exec-yoon` 참석 요청 승인 대기 1건
2. 대조군: `reset_db()` 후 `thread_id` 없이 "2번으로 해줘" → 등록 없음.
3. 분리: 같은 `thread_id`를 `sec-jung`으로 보내면 앞 대화를 이어받지 않음.
4. 서버: uvicorn 백그라운드 + curl(UTF-8 파일, `--data-binary`)로 m-07 두 턴, 2턴 decision 확인 후 종료.
5. 회귀: m-04 단일 턴 동일, `evaluation/check_tools.py` 35개 PASS.
6. 커밋 전 `checkpoints.sqlite`·`schedule.sqlite`·`.env` 제외 확인 → `TASKS 2-1: 대화 기억`.

## 참고
- 5-1 평가 실행기는 문항마다 새 `thread_id`(uuid)를 써야 함(체크포인트는 `reset_db`로 지워지지 않음) → 5-1 계획에 반영.
- 2턴에서 모델이 `find_candidates`를 다시 불러도 DB가 같으니 판정에 지장 없음.

## 결과(2026-10-22)
- m-07 함수 호출(새 uuid thread_id, sec-kim, 2026-10-26)
  - 1턴: 단계 route → 조율.tool_find_candidates → decision, 후보 3개(11-02·11-03·11-04 09:00~10:00), registered_for=[], 8.65초
  - 2턴: 단계 route → 조율.tool_register_event → decision(1턴 단계 중복 없음), registered_for=["exec-kang"], pending_approvals=["exec-yoon"], refused=false, 등록 시각 = 후보 2번(11-03 09:00~10:00), 5.69초
  - DB: 새 일정 1건(host exec-kang), exec-yoon 참석 요청 승인 대기 1건
- 대조군(thread_id 없음)과 분리(같은 thread_id, user sec-jung): 둘 다 등록 없이 "직전에 후보 시간을 찾은 기록이 없다"고 답함
- 서버: m-07 두 턴 모두 HTTP 200, 세 키, 2턴 decision이 위와 같음
- 회귀: check_tools.py 35개 PASS
- 계획과 달라진 점: 없음. 2턴에서 모델은 find_candidates를 다시 부르지 않고 바로 등록했다.

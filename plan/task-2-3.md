# 계획: TASKS 2-3 모델 대체 (`ModelFallbackMiddleware`)

## Context
`build_coordination_agent`는 `model_ids()[0]` 하나만 씁니다. 그 모델이 실패하면(스로틀링, 잘못된 ID, 권한 없음) 요청 전체가 500으로 끝납니다. CLAUDE.md에는 "실패하면 다음 후보로 넘어가 중단 없이 쓴다"고 적혀 있습니다.

1-1 결과에서도 문제가 확인됐습니다. `us` Sonnet 4.5가 `ThrottlingException`을 내고 boto 재시도 4번 때문에 15.4초가 걸렸습니다. 그래서 후속 과제로 "재시도를 줄여 다음 후보로 빨리 넘어간다"가 남아 있습니다.

decision 단계의 `model`도 지금은 실제로 답한 모델이 아니라 `model_ids()[0]`을 적습니다.

목표: 후보 순서대로 자동 전환하고, decision의 `model`에 **실제로 답한 모델**을 적는 것입니다.

## 확인한 사실 (.venv 원본)
- `langchain/agents/middleware/model_fallback.py`의 `ModelFallbackMiddleware(first_model, *additional_models)`
  - 모델 인스턴스를 받을 수 있습니다.
  - 기본 모델이 예외를 내면 넘겨받은 모델을 순서대로 `request.override(model=...)`로 다시 시도하고, 모두 실패하면 마지막 예외를 다시 냅니다.
- `langchain_aws` `ChatBedrockConverse`
  - 응답 `AIMessage.response_metadata["model_name"]`에 모델 ID를 넣습니다. 이 값으로 실제로 답한 모델을 알 수 있습니다.
  - `max_retries`(botocore `retries.max_attempts`) 옵션이 있습니다.

## 변경 파일
1. **`src/agent.py`** (바뀐 부분만)
   - `make_model(model_id)`
     - `max_retries=MODEL_MAX_RETRIES`(새 상수 2)를 넘겨, 스로틀링 때 오래 매달리지 않고 다음 후보로 넘어가게 합니다.
     - `functools.lru_cache`로 같은 ID의 모델을 재사용합니다. 요청마다 후보 10개의 boto 클라이언트를 새로 만들지 않기 위해서입니다.
   - `build_coordination_agent(ctx, llm=None, checkpointer=None)`
     - `llm`이 없으면 `ids = model_ids()`로 기본 모델 `make_model(ids[0])`을 둡니다.
     - 후보가 2개 이상이면 `middleware=[ModelFallbackMiddleware(*[make_model(i) for i in ids[1:]])]`를 붙입니다.
     - `llm`을 주입했을 때(테스트)는 대체를 붙이지 않습니다.
   - `answered_model(messages) -> str | None`(새 함수): 이번 턴 AI 메시지 중 마지막 것의 `response_metadata["model_name"]`을 돌려줍니다.
   - `run_query`: decision의 `model`을 `answered_model(messages)`로 정합니다. 값이 없으면 지금처럼 주입한 모델은 `"injected"`, 그 외에는 `ids[0]`입니다.
   - 모듈 docstring의 지금 구현 범위에 "모델 대체(TASKS 2-3)"를 추가합니다.
2. **`README.md`** 13행: "(구현 예정: TASKS 2-3)"을 지우고, `ModelFallbackMiddleware`로 전환하며 decision의 `model`에 실제로 답한 모델을 적는다고 바꿉니다.
3. **`TASKS.md`** 2-3을 `[x]`로 바꾸고, **`plan/task-2-3.md`**에 이 계획과 결과를 남깁니다.
4. 새 파일과 새 라이브러리는 없습니다(`langchain` 1.4.6에 이미 들어 있음). `.env`도 고치지 않습니다.

## 재사용
- `src/agent.py`: `model_ids`, `make_model`, `_invoke`(이번 턴 메시지만), `judge`, `decision`
- `langchain.agents.middleware.ModelFallbackMiddleware`

## 검증 (명령·출력 원문·읽는 법·PowerShell 재현 명령 함께 보고)
1. **정상**: `reset_db()` 후 m-04를 보내면 decision `model="global.anthropic.claude-sonnet-4-5-20250929-v1:0"`(.env 1순위), 후보 3개입니다.
2. **확인 항목(TASKS)**: 프로세스 환경 변수 `BEDROCK_MODEL_IDS`의 첫 값을 없는 ID(`us.anthropic.no-such-model-v1:0`)로 바꾸고 m-04를 보냅니다. `.env` 파일은 건드리지 않고, 실행 전에 `os.environ`에 넣습니다(`load_dotenv`는 이미 있는 값을 덮어쓰지 않음).
   - 기대: 오류 없이 답하고, decision `model`이 두 번째 후보로 바뀌며, 후보 3개입니다. 응답 시간도 함께 기록합니다.
3. **전부 실패**: 후보를 없는 ID 두 개만 두면 예외가 납니다. 모든 후보가 실패할 때 조용히 넘어가지 않는다는 것을 확인합니다.
4. **회귀**: m-07 두 턴(대화 기억 + 대체 미들웨어), m-21, `check_tools.py` 35개 PASS
5. `reset_db()` → 커밋 전에 `.env`·`db/` 제외 확인 → `TASKS 2-3: 모델 대체`

## 참고
- 서버는 띄우지 않습니다(경로가 같음). 띄울 일이 생기면 포트 8000을 쓰는 프로세스만 끕니다.
- 한 턴 안에서 모델 호출마다 대체가 따로 일어날 수 있습니다. 그래서 decision에는 마지막으로 답한 모델을 적습니다.

## 결과(2026-10-22)
- 확인 항목: `BEDROCK_MODEL_IDS="us.anthropic.no-such-model-v1:0,us.anthropic.claude-haiku-4-5-20251001-v1:0,us.amazon.nova-pro-v1:0"`로 m-04 → 오류 없이 decision `model=us.anthropic.claude-haiku-4-5-20251001-v1:0`, 후보 3개, 6.82초.
- 실제 장애에서도 대체가 동작함: 첫 정상 실행 때 Sonnet 계열이 `ThrottlingException: Too many tokens per day`(일일 토큰 한도)를 내자 global Sonnet 4.5 → us/global Sonnet 4.6을 거쳐 Haiku 4.5가 답함(18.11초, 후보 3개). 이후 global Sonnet 4.5는 회복되어 회귀 실행은 모두 Sonnet 4.5로 처리됨.
- 전부 실패: 없는 ID 두 개만 두면 `ValidationException`을 그대로 냄(3.45초).
- 회귀: m-07 두 턴 PASS(registered_for=[exec-kang], pending=[exec-yoon]), m-21 no_answer=true·후보 0개, check_tools.py 35개 PASS.
- 계획과 달라진 점
  - 첫 대체 검증 때 두 번째 후보(global Sonnet 4.5)도 한도에 걸려 있어, 살아 있는 Haiku를 두 번째 후보로 두고 다시 확인했다.
  - 검증 스크립트를 세션 임시 폴더(scratchpad)에 `m04_model_check.py`로 만들었다(인라인 heredoc이 첫 실행에서 멈춰서). 프로젝트에는 넣지 않음.
- 남은 점(5-5): 한도에 걸린 모델은 `max_retries=2`로도 모델마다 약 4~5초가 걸려, 여러 후보가 연달아 한도에 걸리면 10초를 넘는다. 일일 한도는 재시도로 풀리지 않으므로 5-5에서 재시도 1회 또는 모델 순서 조정을 검토한다.

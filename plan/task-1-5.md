# 계획: TASKS 1-5 서버 `src/app.py`의 `POST /query`

## Context
TASKS 1-4까지 `run_query()`가 제출 스펙 형식(`answer` / `contexts[{doc_id,text}]` / `trace[{step,input,output}]`)을 돌려준다. 제출 규약상 이 결과를 `POST /query`로 받아야 하는데 아직 서버가 없다. README의 아키텍처·실행 방법도 "구현 예정: TASKS 1-5"로 남아 있다.
- 요청 본문: `question` 필수. `user_id`(기본 `sec-kim`), `thread_id`, `base_date`(기본 오늘)는 선택(1-4 계획에서 사용자 결정).
- fastapi·uvicorn 추가는 1-4 계획에서 승인됨. 현재 `.venv`에 uvicorn·starlette·httpx는 fastmcp 의존성으로 이미 있고 **fastapi만 없다**.

## 변경 파일
1. **`src/app.py`(새 파일, TASKS에 명시된 파일)**: 역할은 HTTP 입출력만. 판정·형식은 `src/agent.py`의 `run_query`를 그대로 쓴다.
   - `QueryRequest`(pydantic): `question: str`(`min_length=1`), `user_id: str = "sec-kim"`, `thread_id: str | None = None`, `base_date: date | None = None`
     - `base_date`를 `date` 타입으로 받아 잘못된 날짜·`question` 누락은 FastAPI가 422로 막는다.
     - `thread_id`는 지금은 받기만 하고 쓰지 않는다. 2-1(대화 기억)에서 `run_query`에 넘긴다고 docstring에 적는다.
   - `@app.post("/query")`는 **`def`(동기)**로 둔다. Bedrock 호출이 블로킹이라 FastAPI가 스레드풀에서 돌리게 하기 위해서다.
   - 반환은 `run_query(req.question, req.user_id, req.base_date)`의 dict 그대로(세 키). 모르는 `user_id`도 `run_query`가 거절 응답을 만들므로 200으로 돌려준다.
   - 모델 호출 실패는 지금은 FastAPI 기본 500에 맡긴다(모델 대체는 2-3).
   - 함수·클래스에 한국어 docstring. 모델은 import 시 만들지 않는다(`run_query`가 이미 지연 생성).
2. **`requirements.txt`**: 끝에 `# 서버 (Mini PJT)` 묶음으로 `fastapi`, `uvicorn` 추가(바뀐 줄만). 설치: `.venv/Scripts/python.exe -m pip install fastapi uvicorn`.
3. **`README.md`**(바뀐 줄만)
   - 20행 `POST /query (src/app.py, 구현 예정: TASKS 1-5)` → `POST /query (src/app.py)`
   - 30행 현재 구현 범위 → "서버와 조율 Agent 하나로 질문부터 응답까지(TASKS 1-5까지)"
   - 47행 `서버(구현 예정: TASKS 1-5):` → `서버:`, 실행 명령을 `.venv/Scripts/python.exe -m uvicorn src.app:app --port 8000`로
   - `thread_id`는 2-1부터 쓰인다는 말을 53행에 덧붙임
4. **`src/agent.py`**: 바꾸지 않는다.
5. **`TASKS.md`**: 확인 통과 후 1-5를 `[x]`.
6. **`plan/task-1-5.md`**: 승인 직후 이 계획을 저장하고, 끝에 결과를 덧붙여 최종본으로 갱신.

## 재사용
- `src/agent.py`의 `run_query`(응답 3키 생성, 모르는 사용자 거절, `_to_date`가 `date`도 받음), `decision()`(검증 시 decision 단계 확인)

## 검증(명령·출력 원문·읽는 법·PowerShell 재현 명령을 함께 보여 줌)
1. 서버 기동(백그라운드): `.venv/Scripts/python.exe -m uvicorn src.app:app --port 8000`
2. m-04 (Git Bash curl, 한글 UTF-8 그대로 전송):
   `curl -s -w "\nHTTP %{http_code}\n" -X POST localhost:8000/query -H "Content-Type: application/json" -d '{"question":"다음 주에 강민준 부사장님과 윤서연 전무님 1시간 회의 잡아줘","user_id":"sec-kim","base_date":"2026-10-26"}'`
   - 기대: `HTTP 200`, 최상위 키가 정확히 `answer`·`contexts`·`trace`, decision 단계 `route="조율"`, `refused=false`, `candidates` 1~3개(11-02~11-06, 60분)
   - PowerShell 재현: `Invoke-WebRequest -UseBasicParsing -Method Post -Uri http://localhost:8000/query -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes('{...}'))` 후 `.StatusCode`, `.Content`
3. 오류 경로: `question` 없음 → 422, `base_date: "2026-13-01"` → 422, 모르는 `user_id` → 200 + decision `refused=true`(LLM 호출 없음)
4. 회귀: `python evaluation/check_tools.py` 35개 통과
5. 서버 종료 → TASKS 1-5 `[x]` → `plan/task-1-5.md` 결과 기록 → 커밋 `TASKS 1-5: 서버 POST /query`

## 결과(2026-10-22)
- fastapi 0.159.1 설치(uvicorn 0.54.0은 이미 있었음). requirements에 `fastapi`, `uvicorn` 추가.
- m-04를 서버로 보냄: HTTP 200, 최상위 키 `answer`·`contexts`·`trace`, 단계 route → 조율.tool_find_candidates → decision, decision `route="조율"`, `refused=false`, 후보 3개(11-02·11-03·11-04 09:00~10:00), decision의 candidates가 도구 단계 output과 같음, 8.17초.
- 오류 경로: question 없음 422, `base_date="2026-13-01"` 422, 모르는 user_id는 200 + auth·decision 두 단계, `refused=true`.
- PowerShell `Invoke-WebRequest`(UTF-8 바이트 본문)로도 200과 세 키 확인.
- 회귀: `check_tools.py` 35개 PASS.
- 계획과 달라진 점: Git Bash에서 한글 본문을 `curl -d '...'`로 바로 넣으면 UTF-8이 아니게 넘어가 400("error parsing the body")이 났다. 본문을 UTF-8 파일로 저장해 `--data-binary @파일`로 보내 확인했고, README 실행 방법에 이 주의를 한 줄 덧붙였다.

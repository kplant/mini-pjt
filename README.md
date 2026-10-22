# 미니 PJT: 임원 일정 관리 Agent

## 무엇을 푸나
비서가 회의 하나를 잡으려면 상대 임원 쪽 비서에게 가능한 시간을 묻고 맞추느라 한 건에 약 10분이 걸리고, 외부 참석자 정보는 찾을 곳이 없다. 이 Agent는 자연어 요청 한 번으로 참석자 모두가 비어 있는 후보 시간과 참석자 프로필을 권한 규칙에 맞게 돌려준다.

- 사용자: OO사업부 임원 70~80명, 비서 100명 내외, 관리자 2명
- 서비스 스펙: [SERVICE.md](SERVICE.md) · 용어: [CONTEXT.md](CONTEXT.md) · 작업 순서: [TASKS.md](TASKS.md)

## 활용한 패턴 (Day 1~7)
- Day 1 결정적 규칙: LLM은 문장만 쓰고, 권한·후보 시간·날짜 계산은 코드가 한다(`src/tools.py`, `src/agent.py`의 `date_hints`).
- Day 2 RAG: 외부 인물·회사 소개 자료를 Titan 임베딩과 Chroma로 검색한다. 질문 대상의 자료가 없으면 검색하지 않고 `no_answer`를 낸다(`assess_retrieval` 아이디어, `src/retriever.py`). 검색 단계는 trace에서 `retrieve`로, 근거 문서는 `contexts`의 `doc_id`(파일명)로 남긴다.
- Day 3 도구 Agent: `create_agent`와 도구 호출로 조율한다(`build_coordination_agent`).
- Day 4 실패 복구: 후보 모델 10개를 `ModelFallbackMiddleware`로 순서대로 자동 전환하고, decision 단계의 `model`에 실제로 답한 모델을 적는다.
- Day 5 가드레일·승인: 역할, 담당 관계, 비공개 검사를 도구 안에서 한다. 다른 임원의 캘린더를 바꾸는 요청은 승인 대기로 둔다([ADR 0002](docs/adr/0002-승인은-대화가-아니라-업무-데이터.md)). 거절 여부(`refused`)는 도구가 돌려준 `denied`로만 정하고, 요청 문장 속 자기소개는 믿지 않는다. 등록되지 않은 사용자는 LLM을 부르지 않고 거절한다. 연락처는 `answer`와 `contexts`에는 그대로 두고 trace에서만 일부를 가린다(예: `010-****-5678`, `p***@abc.example`, [ADR 0004](docs/adr/0004-연락처는-마스킹하지-않는다.md)).
- Day 6 Supervisor: 조율·일정·관리 하위 Agent를 도구로 감싼 Supervisor(`create_agent`). 하위 Agent에는 원래 질문을 그대로 넘기고 그 답을 다시 쓰지 않는다(`return_direct`). Supervisor도 하위 Agent와 같은 모델 후보 순서를 쓰고, `.env`의 `SUPERVISOR_MODEL_ID`로 1순위만 바꿀 수 있다. 조율 Agent, 일정 Agent(조회·브리핑, 변경·취소·불참·승인, 프로필·외부 인물 등록·소개 자료 검색), 관리 Agent(담당 관계)를 모두 연결했다.
- Day 7 계측·평가: trace를 단계로 기록하고, 평가셋 24문항을 3회 돌려 라운드 리포트를 남긴다(구현 예정: TASKS 5번).

## 아키텍처
```
POST /query (src/app.py)
  └ run_query (src/agent.py): 요청자 확인(사용자 목록) → Supervisor
       ├ 조율 Agent: 후보 시간 · 바쁨 · 등록
       ├ 일정 Agent: 조회 · 브리핑 · 변경 · 승인 · 프로필 · 소개 자료 검색(src/retriever.py)
       └ 관리 Agent: 담당 관계
            └ 도구(src/tools.py): 권한 검사 → SQLite(src/db.py)
  → {"answer", "contexts": [{"doc_id", "text"}], "trace": [{"step", "input", "output"}]}
```
- 권한은 프롬프트가 아니라 도구 코드가 SQLite에서 읽은 뒤 걸러서 넘긴다. 권한 밖의 데이터는 도구 밖으로 나가지 않는다([ADR 0003](docs/adr/0003-supervisor-구조-권한은-도구-계층.md)).
- 평가 판정 값(route, refused, candidates, pending_approvals, model, latency_s)은 trace의 마지막 `decision` 단계에 담는다.
- 현재 구현 범위: 서버 → Supervisor → 조율·일정·관리 Agent로 질문부터 응답까지(TASKS 3-5까지).

## 실행 방법
```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
# Python 3.14: ragas의 의존 패키지 scikit-network가 빌드되지 않으므로, 위 설치가 실패하면 ragas 줄을 빼고 설치한 뒤
#   .venv/Scripts/python.exe -m pip install ragas==0.4.3 --no-deps 후 datasets tiktoken instructor diskcache appdirs nest-asyncio typer langchain_openai 설치

# .env: AWS 자격 증명(Bedrock, us-east-1). 선택: BEDROCK_MODEL_IDS=모델1,모델2,...(후보 순서 덮어쓰기)

.venv/Scripts/python.exe src/db.py                 # 교육용 더미 데이터로 DB 초기화
.venv/Scripts/python.exe -m src.agent              # 후보 모델 사용 가능 여부 확인
.venv/Scripts/python.exe evaluation/check_tools.py # 도구·권한·RAG 검사(LLM 호출 없음)
.venv/Scripts/python.exe evaluation/run_eval.py   # 평가셋 24문항 실행·판정(--runs 3, --ids m-01,m-04)
.venv/Scripts/python.exe evaluation/run_eval.py --ragas   # RAGAS 4개 지표 함께 계산(조회·브리핑, 소개 자료 RAG 문항)
```
질의 한 번(지금 단계):
```bash
.venv/Scripts/python.exe -c "import json; from src.agent import run_query; print(json.dumps(run_query('다음 주에 강민준 부사장님과 윤서연 전무님 1시간 회의 잡아줘', 'sec-kim', '2026-10-26'), ensure_ascii=False, indent=2))"
```
서버:
```bash
.venv/Scripts/python.exe -m uvicorn src.app:app --port 8000
curl -X POST localhost:8000/query -H "Content-Type: application/json" \
     -d '{"question": "다음 주에 강민준 부사장님과 윤서연 전무님 1시간 회의 잡아줘", "user_id": "sec-kim", "base_date": "2026-10-26"}'
```
요청 본문은 `question`이 필수이고, `user_id`(기본 `sec-kim`), `thread_id`, `base_date`(기본 오늘)는 선택이다. 같은 `user_id`·`thread_id`로 보내면 이전 대화를 이어 간다(`db/checkpoints.sqlite`). `thread_id`가 없으면 기억 없이 한 번만 처리한다.
Windows Git Bash에서 한글을 `-d`로 바로 넣으면 UTF-8이 아니게 넘어가 400이 난다. 본문을 UTF-8 파일로 저장해 `--data-binary @m04.json`으로 보내거나, PowerShell에서는 `Invoke-WebRequest ... -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))`로 보낸다.

## RAGAS 평가 결과
측정 전(TASKS 5-2). 대상은 근거 문서가 있는 문항(소개 자료 RAG, 조회·브리핑)이다.
- context_recall: 측정 전
- context_precision: 측정 전
- faithfulness: 측정 전
- answer_relevancy: 측정 전

## 인-아웃 세트 통과율 (자체 평가)
평가셋은 [evaluation/test_queries.csv](evaluation/test_queries.csv)의 24문항이다(guardrail 4, no_answer 3 포함). 성공 기준은 3회 실행해 3회 모두 22/24 이상이다.
- 1차 (Day 9 종료): 측정 전 / 24
- 2차 (Day 10 개선 후): 측정 전 / 24
- 개선폭: 측정 후 기록

## 트라이앤에러 회고
- 시도했지만 버린 접근
  - 역할별로 도구를 숨겨 권한을 막는 방식: 도구가 없으면 거절 신호(`denied`)가 사라져, 거절 여부를 답변 문장으로 추측해야 해서 버렸다.
  - 벡터 검색만으로 소개 자료를 찾는 방식: 자료가 없는 회사를 물어도 비슷한 다른 회사 문서가 나와, 대상 판정을 먼저 하도록 바꿨다.
  - Supervisor를 직접 만든 `StateGraph`로 짜는 방식: 제출 규약(`create_agent`) 때문에, 하위 Agent를 도구로 감싸는 방식으로 바꿨다.
  - DB를 파일 삭제로 초기화하는 방식: Windows에서 파일이 잠겨 실패해, 테이블을 다시 만드는 방식으로 바꿨다.
  - 첫 후보 모델(us Sonnet 4.5): 스로틀링으로 15초가 걸려, 개발 중에는 `BEDROCK_MODEL_IDS`로 순서를 바꿨다.
- 최종 채택한 접근: 권한과 계산은 도구 코드에서 걸러서 넘기고([ADR 0003](docs/adr/0003-supervisor-구조-권한은-도구-계층.md)), 승인은 대화 상태가 아니라 업무 데이터로 다룬다([ADR 0002](docs/adr/0002-승인은-대화가-아니라-업무-데이터.md)).
- 남은 한계 · 향후 개선 방향
  - 응답이 약 8초로 10초 기준에 가깝다. Supervisor를 더하면 넘을 수 있어 TASKS 5-5에서 대응한다.
  - 인증 없이 요청의 `user_id`를 믿는다.
  - 실제 사내 일정 도구와 외부 인물 DB는 연결하지 않았다. 저장소 인터페이스(`src/db.py`)와 `src/retriever.py`가 바꿀 자리다.

## 핵심 코드 위치
- `src/agent.py:240` — `run_query`: 요청 처리와 응답 형식(answer / contexts / trace)
- `src/agent.py:139` — `build_coordination_agent`: 조율 Agent
- `src/agent.py:187` — `judge`: 도구 결과로 판정(decision 단계)
- `src/tools.py:161` — `_can_view`: 일정 열람 권한
- `src/tools.py:325` — `find_candidates`: 후보 시간 계산
- `src/tools.py:726` — `build_tools`: 하위 Agent별 도구 묶음
- `src/retriever.py:111` — `search_intro`: 소개 자료 RAG(대상 판정 후 검색)
- `src/db.py:127` — `reset_db`: 더미 데이터 초기화
- `evaluation/test_queries.csv` — 평가셋 24문항, `evaluation/check_tools.py` — 도구 검사
- `docs/adr/` — 설계 결정 기록

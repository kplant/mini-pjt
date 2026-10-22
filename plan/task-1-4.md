# 계획: 제출 스펙 맞추기(폴더 구조 → TASKS 재구성 → 1-4 API 스펙 맞춤)

## Context
사용자가 공식 제출 스펙을 공유했다. API 형식, 필수 산출물 구조, README §4-5 템플릿이다. 지금 구현과 다른 점은 다섯 가지다.
- 폴더 이름: `mini-pjt_{본인이름}`이어야 한다.
- `contexts` 키: `doc_id`/`text`여야 한다.
- `trace`: 단계 목록 `[{step, input, output}]`이어야 한다.
- 서버 위치: 산출물 구조에 서버 파일 자리가 없다.
- README: RAGAS 지표를 요구한다.

사용자 결정은 다음과 같다.
- 폴더 이름은 **`mini-pjt_김상열`**이고 **지금** 바꾼다.
- 스펙에 없는 파일(CLAUDE.md, CONTEXT.md, TASKS.md, docs/adr/, plan/)은 그대로 둔다.
- Dockerfile과 run.sh를 **둘 다** 만든다(TASKS 6번).
- trace는 단계로 풀고, 판정 값은 마지막 `decision` 단계에 담는다.
- 요청 본문은 `question`이 필수이고, `user_id`·`thread_id`·`base_date`는 선택이다.
- ragas 도입을 허락한다.
- `test_queries.csv`는 지금 스키마를 유지한다.

작업은 A → B → C 순서로 하고, 단계마다 커밋한다.

## A. 폴더 구조 맞추기(커밋: `구조: 폴더 이름을 mini-pjt_김상열로`)
1. `C:\Users\SDS\Desktop\mini-pjt`를 `C:\Users\SDS\Desktop\mini-pjt_김상열`로 바꾼다(`mv`).
   - VS Code나 다른 프로세스가 파일을 잡고 있어 실패하면 멈추고, 사용자에게 VS Code에서 폴더를 닫아 달라고 요청한다.
   - git 이력은 `.git`이 함께 옮겨지므로 그대로 남는다.
2. `.venv`를 다시 만든다. 기존 `.venv`에는 옛 경로가 박혀 있다.
   - 기존 `.venv`를 지운다.
   - `python -m venv .venv`(Python 3.14, 기존과 같은 버전)
   - `pip install -r requirements.txt`
3. `chroma_db/`와 `schedule.sqlite`는 gitignore 대상 산출물이라 그대로 옮겨진다. 경로가 코드 안의 상대 경로(`ROOT` 기준)라 수정할 필요가 없다.
4. 폴더 이름이 적힌 곳을 고친다(바뀐 줄만).
   - `docs/adr/0001`: "`mini-pjt` 저장소" → "`mini-pjt_김상열`". 제출 방식 문장은 6-2에서 다시 정한다는 메모를 단다.
   - 메모리 파일 3개(`commit-per-task`, `plan-folder-per-task`, `ask-before-new-files`)의 경로
5. 확인
   - 새 폴더에서 `git log --oneline -3`
   - `python evaluation/check_tools.py`가 35개 통과
   - `python -m src.agent`로 모델 확인 1회
6. 이후 작업은 모두 새 폴더 경로에서 한다. 사용자는 VS Code에서 새 폴더를 다시 열어야 한다.

## B. TASKS.md 재구성(바뀐 부분만, 커밋: `TASKS: 제출 스펙 반영`)
- 맨 위 기준 문서에 "공식 제출 스펙(API 형식, 산출물 구조, README §4-5)"을 추가한다.
- 1번 묶음
  - **1-4 API 스펙 맞춤**(새 작업, C에서 함)
    - 확인: m-04 응답의 `contexts` 키가 `doc_id`·`text`이고, `trace`의 모든 단계가 `step`·`input`·`output`뿐이며, `decision` 단계의 `candidates`가 도구 결과와 같음
  - **1-5 서버 `src/app.py`**(기존 1-4를 옮김)
    - 실행: `uvicorn src.app:app`. requirements에 fastapi·uvicorn을 추가한다.
    - 확인: curl로 m-04를 보내면 200과 세 키가 돌아옴
  - **1-6 README 초안**
    - §4-5 템플릿의 제목 순서대로, 확정된 내용을 채우고 수치 칸은 "측정 전"으로 둔다.
    - 확인: 템플릿의 제목 9개가 순서대로 있고, 수치 칸 말고 빈 칸이 없음
- 5번 묶음
  - 5-1 다음에 **5-2 RAGAS 측정**을 넣는다.
    - ragas를 추가하고, 평가자는 Bedrock 모델과 Titan 임베딩으로 한다. 대상은 근거 문서가 있는 문항이다.
    - Python 3.14 호환은 그때 확인한다.
    - 확인: 4개 지표 값이 라운드 리포트에 나옴
  - 이후 번호를 민다: 5-3 round1 → 5-4 고치기/round2 → 5-5 응답 시간
- 6번 묶음
  - 6-1 README 완성(수치)
  - 6-2 제출 방식 확인 후 제출(별도 저장소인지, `sds-ax-training/miniprj/` 복사인지). ADR 0001을 그때 고친다.
  - **6-3 `run.sh`**: 서버 실행과 평가 실행
    - 확인: Git Bash에서 `bash run.sh serve`로 서버가 뜨고 curl m-04가 200
  - **6-4 `Dockerfile`**: 클린 환경 재현. AWS 자격 증명은 이미지에 넣지 않고 실행할 때 환경 변수로 넘긴다.
    - 확인: `docker build` 후 `docker run -p 8000:8000 --env-file .env`로 curl m-04가 200. 이 PC에 Docker가 없으면 사용자에게 보고하고 확인 방법을 정한다.
  - 6-5 시연 리허설
- 확인 줄에 있는 `trace.route` 같은 표현은 "trace의 decision 단계 route"로 고친다.

## C. 1-4 API 스펙 맞춤: `src/agent.py`(커밋: `TASKS 1-4: API 스펙 맞춤`)
- `build_contexts(calls)` → `[{"doc_id": 도구 이름, "text": 결과 JSON 문자열}]`. 3-4부터는 소개 자료 파일명이 `doc_id`가 된다.
- `build_trace(...)` → 단계 목록
  1. `{"step": "route", "input": 질문, "output": "조율"}`
  2. 도구 호출마다 `{"step": "조율.<도구 이름>", "input": args, "output": result}`
  3. `{"step": "decision", "input": "도구 결과로 판정", "output": {route, refused, no_answer, candidates, registered_for, pending_approvals, model, latency_s}}`
- `decision(trace) -> dict`: decision 단계의 output을 꺼낸다. 평가기와 테스트가 쓴다.
- 판정 규칙은 1-3과 같다(도구 결과로만 정함).
- 모르는 사용자: `[{"step": "auth", "input": user_id, "output": "등록되지 않은 사용자"}, decision 단계(refused=True, route=None, model=None)]`
- 문서 반영(바뀐 줄만)
  - `SERVICE.md` 5번: "`trace`" → "`trace`의 decision 단계", "`trace.route`" → "decision 단계의 `route`"
  - `evaluation/eval-fixtures.md`: 판정 필드는 decision 단계에서 읽는다고 고치고, `expected_source`는 `contexts`의 `doc_id`라고 고친다.
  - `docs/adr/0003`: "응답 `trace`의 `route`" → "응답 trace의 decision 단계 `route`"
- `plan/task-1-4.md`에 이 계획과 결과를 저장한다.

## D. README.md를 프로젝트 내용으로 바꾸기(= TASKS 1-6, 커밋: `TASKS 1-6: README 초안`)
지금 `README.md`는 §4-5 템플릿 예시다. **제목 9개와 그 순서는 그대로 두고** 내용만 이 프로젝트에 맞게 채운다. 템플릿 전체를 갈아 끼우게 되므로 사용자의 이번 요청을 승인으로 본다. 아직 없는 기능은 "(구현 예정: TASKS n-n)"으로 표시해, 문서가 실제 상태보다 앞서 나가지 않게 한다.

| 제목 | 채울 내용 |
|---|---|
| `# 미니 PJT: …` | `임원 일정 관리 Agent` |
| 무엇을 푸나 | 비서가 회의 하나를 잡으려면 상대 임원 쪽 비서에게 가능한 시간을 묻고 맞추느라 한 건에 약 10분이 걸리고, 외부 참석자 정보는 찾을 곳이 없다. 자연어 요청 한 번으로 참석자 모두가 비어 있는 후보 시간과 참석자 프로필을 권한 규칙에 맞게 돌려준다. |
| 활용한 패턴 (Day 1~7) | 아래 목록 |
| 아키텍처 | 아래 텍스트 다이어그램과 "현재 구현 범위" 한 줄 |
| 실행 방법 | 설치(`python -m venv .venv`, `pip install -r requirements.txt`), `.env`(AWS 자격 증명, 선택 `BEDROCK_MODEL_IDS`), DB 초기화(`python src/db.py`), 서버(`uvicorn src.app:app`, 1-5 이후), curl 예시, 도구 검사(`python evaluation/check_tools.py`) |
| RAGAS 평가 결과 | 4개 지표 이름은 두고 값은 "측정 전 (TASKS 5-2)" |
| 인-아웃 세트 통과율 | 1차·2차 "측정 전 / 24", 개선폭 "측정 후 기록" |
| 트라이앤에러 회고 | 아래 목록 |
| 핵심 코드 위치 | `src/agent.py:<run_query 줄 번호>`(쓸 때 grep으로 확인), `src/tools.py`, `src/retriever.py`, `src/db.py`, `evaluation/test_queries.csv`, `docs/adr/` |

**활용한 패턴**
- Day 1 결정적 규칙: LLM은 문장만 쓰고, 권한·후보 시간·날짜 계산은 코드가 한다(`src/tools.py`, `date_hints`).
- Day 2 RAG: 외부 인물·회사 소개 자료를 Titan + Chroma로 검색한다. 대상 문서가 없으면 검색하지 않고 `no_answer`를 낸다(`assess_retrieval` 아이디어).
- Day 3 도구 Agent: `create_agent`와 도구 호출로 조율한다.
- Day 4 실패 복구: 후보 모델 10개를 자동으로 바꿔 가며 쓴다(구현 예정: 2-3).
- Day 5 가드레일·승인: 역할, 담당, 비공개 검사를 도구 안에서 하고, 다른 임원 캘린더 변경은 승인 대기로 둔다(ADR 0002). 연락처는 trace에서만 마스킹한다(구현 예정: 4-2).
- Day 6 Supervisor: 조율·일정·관리 하위 Agent를 도구로 감싼 Supervisor(구현 예정: 3-1).
- Day 7 계측·평가: trace를 단계로 기록하고, 24문항을 3회 돌려 라운드 리포트를 남긴다(구현 예정: 5번).

**아키텍처**(텍스트)
```
POST /query (src/app.py)
  └ run_query (src/agent.py): 요청자 확인(사용자 목록) → Supervisor
       ├ 조율 Agent: 후보 시간·바쁨·등록
       ├ 일정 Agent: 조회·브리핑·변경·승인·프로필·소개 자료 검색(src/retriever.py)
       └ 관리 Agent: 담당 관계
            └ 도구(src/tools.py): 권한 검사 → SQLite(src/db.py)
  → {answer, contexts, trace}
```
현재 구현 범위: 조율 Agent 하나로 질문부터 답변까지(TASKS 1-4까지).

**트라이앤에러 회고**(지금까지 실제로 있었던 일)
- 시도했지만 버린 접근
  - 역할별로 도구를 숨겨 권한을 막는 방식: 도구가 없으면 거절 신호(`denied`)가 사라져, 거절 여부를 답변 문장으로 추측해야 해서 버렸다.
  - 벡터 검색만으로 소개 자료를 찾는 방식: 자료가 없는 회사를 물어도 비슷한 다른 회사 문서가 나와, 대상 판정을 먼저 하도록 바꿨다.
  - Supervisor를 직접 만든 `StateGraph`로 짜는 방식: 제출 규약(`create_agent`) 때문에, 하위 Agent를 도구로 감싸는 방식으로 바꿨다.
  - DB를 파일 삭제로 초기화하는 방식: Windows에서 파일이 잠겨 실패해, 테이블을 다시 만드는 방식으로 바꿨다.
  - 첫 후보 모델(us Sonnet 4.5): 스로틀링으로 15초가 걸려, 개발 중에는 순서를 바꿨다.
- 최종 채택한 접근: 권한과 계산은 도구 코드에서 걸러서 넘기고(ADR 0003), 승인은 대화 상태가 아니라 업무 데이터로 다룬다(ADR 0002).
- 남은 한계
  - 응답 8초로 10초 기준에 가깝다.
  - 인증 없이 `user_id`를 믿는다.
  - 실제 사내 일정 도구와 외부 인물 DB는 연결하지 않았다.

확인: §4-5 제목 9개가 순서대로 있고, 수치 칸 말고는 템플릿 예시 문구(`[프로젝트 이름]`, `Day X`, `0.XX` 등)가 남아 있지 않음. `grep -n "\[프로젝트 이름\]\|Day X\|0\.XX\|NN" README.md`의 결과가 0줄이어야 한다. RAGAS 줄만 예외로, "측정 전"으로 바뀌어 있어야 한다.

순서: A(폴더) → B(TASKS) → C(1-4) → D(README, 1-6). 1-5(서버)는 그다음 차례에 한다.

## 재사용
- `src/agent.py`의 `collect_tool_calls`, `_merge_unique`, `_result`(1-3). 판정 로직은 그대로 두고 담는 형식만 바꾼다.

## 검증(명령과 출력을 그대로 보여 준다)
1. A가 끝나면 새 폴더에서 git 이력, `check_tools.py` 35개, 모델 확인을 본다.
2. C: LLM 없이 손으로 만든 메시지로 확인한다.
   - 모든 단계가 `step`·`input`·`output` 세 키뿐인지
   - `decision()`의 값이 1-3 결과와 같은지
3. C: 실제 Bedrock으로 m-04를 돌려 응답 JSON 전체를 출력한다.
   - 최상위 키 3개, `contexts` 키가 `doc_id`·`text`, `decision.candidates`가 도구 단계 output과 같음
4. C: 모르는 사용자는 `auth`와 `decision` 두 단계, `refused=True`
5. `check_tools.py` 35개 통과. 그 뒤 TASKS 1-4를 `[x]`로 표시하고 커밋한다.

## 결과(2026-10-22)
- A(폴더 이름 변경): VS Code와 Claude Code 세션이 폴더를 열고 있어 `Device or resource busy`로 실패했다. 사용자 결정으로 **보류**하고 TASKS 6-2로 옮겼다. ADR 0001과 메모리 경로는 바꾸지 않았다.
- B(TASKS 재구성): 커밋 `5f3b298`
- C(1-4)
  - LLM 없이 확인: 단계는 route → 도구 4개 → decision 순서이고, 모든 단계의 키가 step·input·output뿐이다. decision 값은 1-3과 같다(refused=True, 마지막 후보, 승인 대기 중복 제거). contexts 키는 doc_id·text.
  - 실제 Bedrock m-04: 최상위 키 3개, `contexts` 키 doc_id·text, `decision.candidates`가 도구 단계 output과 같음, 8.49초
  - 모르는 사용자: auth와 decision 두 단계, refused=True
  - 문서: SERVICE.md 5번, eval-fixtures.md, ADR 0003의 trace 표현을 decision 단계로 바꿨다.
  - 회귀: `check_tools.py` 35개 통과
- 코드에서 달라진 점: 판정 함수 이름을 `judge()`로 분리했다. `build_trace(question, calls, verdict)`는 단계 목록만 만든다.

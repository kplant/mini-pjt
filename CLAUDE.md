# 프로젝트 규칙

## 기술 스택
- Python, LangChain, LangGraph
- 모델은 Amazon Bedrock (ChatBedrockConverse)
- Agent 생성은 langchain.agents 의 create_agent 를 쓴다

## 폴더 구조 (제출 규약. 바꾸지 않는다)
src/agent.py       메인 에이전트 그래프
src/tools.py       도메인 도구
src/retriever.py   RAG 파이프라인
data/              사용한 문서와 데이터
evaluation/        test_queries.csv 와 평가 리포트

## 주고받는 형식 (제출 규약)
- POST /query 로 받고 question 필드를 읽는다
- 답은 answer, contexts, trace 세 키로 돌려준다

## 코드 규칙
- 파일 하나에 한 가지 역할만 둔다
- 함수와 도구에는 한국어 docstring 을 쓴다
- 비밀 값은 .env 에서 읽고 코드에 적지 않는다

## 하지 말 것
- 요청하지 않은 파일을 새로 만들지 않는다
- 기존 파일을 통째로 다시 쓰지 않는다. 바뀐 부분만 고친다


# 작업 규칙

- 무엇을 만드는지는 SERVICE.md가 기준이다. 애매하면 추측하지 말고 물어본다.

- 스택: Python, LangGraph, Bedrock (기본 us.anthropic.claude-sonnet-4-5-20250929-v1:0) -> 후보 10개와 순서는 src/agent.py의 MODEL_IDS에 두고, .env의 BEDROCK_MODEL_IDS로 덮어쓸 수 있다. 실패하면 다음 후보로 넘어가 중단 없이 쓴다. Supervisor도 같은 후보 순서를 쓰며, .env의 SUPERVISOR_MODEL_ID로 Supervisor의 1순위만 바꿀 수 있다.

- 괜찮은 레퍼런스 코드를 깃허브에서 찾아서 레퍼런스로 삼거나 (있을 경우) 현재 ref 폴더 내 코드를 참조한다. 절대 사용자의 허락없이 신규 프레임워크 또는 라이브러리를 들이지 않는다.

- 한 번에 TASKS.md의 작업 하나만 한다.

- 계산, 규칙 판정은 LLM이 아니라 파이썬 코드로 하는 원칙으로 진행한다. 필요시 LLM 판정부분을 덧붙여 추가한다.

- API 키는 .env에서 읽는다.

## 세션 시작 시
- TASKS.md에서 첫 번째 `[ ]` 작업이 다음 작업이다. 직전 작업의 결과는 plan/task-N-N.md 끝의 "결과"에 있다.
- 공식 제출 스펙(API 형식, 산출물 구조)은 docs/submission-spec.md에 있다.

## 작업 흐름
- 계획 → 승인 → plan/task-N-N.md에 저장 → 구현 → TASKS의 "확인" 통과 → `[x]` → plan 파일 끝에 결과(계획과 달라진 점) 추가 → commit `TASKS N-N: 요약`
- 계획이 바뀌면 plan 파일을 최종본으로 덮어쓴다. push는 요청할 때만 한다.
- commit 전에 .env, chroma_db/, db/가 빠지는지 확인한다.
- 요청하지 않은 파일이 필요하면 경로와 목적을 먼저 묻는다(임시 폴더에 몰래 만들지 않는다).
- 테스트 보고: 실행한 명령, 출력 원문, 읽는 법, PowerShell 재현 명령을 함께 보여 준다.
- 답변은 한국어로 한다. 명령·출력 원문은 그대로 둔다.
- 질문은 가능하면 grill-with-docs 방식(`mattpocock-skills:grilling` + `mattpocock-skills:domain-modeling` 스킬)으로 하고, 정해진 용어·결정은 CONTEXT.md와 docs/adr/에 남긴다. 단순한 선택지 확인은 선택지 질문으로 충분하다.

## 개발 환경
- Windows. Python은 `.venv/Scripts/python.exe`(3.14)를 쓴다.
- `.env`의 BEDROCK_MODEL_IDS가 global Sonnet 4.5를 1순위로 덮어쓴다(us는 스로틀링). decision 단계의 model이 global로 나오는 것은 정상이다.
- 서버 확인: uvicorn을 백그라운드로 띄우고 curl을 보낸 뒤 종료한다. Git Bash에서 한글 본문은 UTF-8 파일로 만들어 `--data-binary @파일`로 보낸다(`-d '...'`로 바로 넣으면 400).
- m-04 응답은 약 8초다(기준 10초).
- 회귀 검사: `evaluation/check_tools.py`가 35개 PASS여야 한다.
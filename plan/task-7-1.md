# 계획: TASKS 7-1 Langfuse trace (self-host)

## 상태: 완료(2026-10-23, Docker Desktop 설치 후 재개)

## Context
- 사용자 요청(2026-10-23): Langfuse 적용
- 사용자 결정: ① 서버는 직접 띄움(self-host) ② 먼저 trace만(평가 점수 업로드는 다음 단계) ③ `langfuse` 패키지 추가 승인
- 확인한 것
  - `pip install --dry-run langfuse`: langfuse 5.0.4 + backoff, opentelemetry-exporter-otlp-proto-http, opentelemetry-exporter-http-transport, wrapt — Python 3.14에서 풀림(C 확장 빌드 없음). 실제 설치는 아직
  - Langfuse 서버 v3는 Postgres·ClickHouse·Redis·MinIO를 함께 띄워야 해 `docker compose`가 필요. 이 PC에는 Docker·WSL 없음(6-4에서 확인)
  - `systeminfo`에 "하이퍼바이저가 검색되었습니다" → 가상 머신이면 Docker Desktop(WSL2)에 중첩 가상화가 필요할 수 있음
  - 교육 저장소(sds-ax-training, sds-ax-practice)에 참고할 Langfuse 코드 없음, `.env`에 Langfuse 키 없음

## 재개 전 정할 것
- Langfuse `docker-compose.yml` 위치: 프로젝트 밖(예: `C:\Users\SDS\langfuse\`, 추천) 또는 프로젝트 안(`infra/langfuse/`, 커밋)

## 순서
1. (사용자) Docker Desktop 설치: 관리자 PowerShell에서 `wsl --install` → 재부팅 → Docker Desktop 설치 → `docker run hello-world`. 안 되면(중첩 가상화 등) 다른 방법을 정함
2. Langfuse 공식 `docker-compose.yml`로 서버 기동 → `http://localhost:3000`
3. (사용자) 브라우저에서 계정·조직·프로젝트 생성, API 키 발급 → `.env`에 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST=http://localhost:3000`
4. `requirements.txt`에 `langfuse`(버전 고정 여부는 설치 시 결정), `.venv`에 설치
5. `src/agent.py`
   - `run_query`에서 Supervisor 실행 config의 callbacks에 Langfuse `CallbackHandler`를 추가. 요청자(user_id)·thread_id·route를 메타데이터/태그로
   - `.env`에 키가 있을 때만 켜짐(없으면 지금과 동일 → 제출본·평가·Docker 영향 없음). 모듈 import 시 만들지 않고 지연 생성
   - 하위 Agent는 Supervisor 도구 안에서 따로 `invoke`되므로 같은 trace에 들어오는지 확인. 안 들어오면 하위 Agent config에도 같은 핸들러를 넘김(StepTimer와 함께)
   - 연락처 마스킹(ADR 0004: 사람이 직접 보지 않는 기록은 가림): Langfuse 클라이언트의 mask 기능에 `mask_pii` 연결
6. README 실행 방법·Langfuse 절, TASKS 7-1 `[x]`, 이 파일에 결과

## 검증
1. m-04, m-07(두 턴, 같은 thread_id)을 보내 Langfuse 화면에서 trace 트리(Supervisor → 하위 Agent → 모델 호출·도구 호출)와 입력·출력·소요 시간 확인, 연락처 질문(m-13)은 가려져 보이는지
2. 키를 지우고 m-04 → 지금과 같은 응답·trace, `check_tools.py` 39개 PASS
3. Langfuse를 켰을 때 응답 시간 변화(m-04 몇 회)
4. 커밋 `TASKS 7-1: Langfuse trace`(push는 요청 시)

## 다음 단계(7-1 이후 후보)
- `run_eval.py`의 규칙 판정·RAGAS·LLM-as-Judge 점수를 Langfuse score로 업로드, 평가셋을 Langfuse dataset으로

## 결과(2026-10-23)
- Docker: 29.9.2(Linux 엔진, 메모리 8.3GB, CPU 12), Compose v5.6.1, hello-world 성공
- 사용자 결정: compose 파일은 프로젝트 밖 `C:\Users\SDS\langfuse\`
  - 공식 `docker-compose.yml`(Langfuse v4 이미지 + Postgres·ClickHouse·Redis·MinIO)은 그대로, `.env`(무작위 비밀번호 11개, CHANGEME 기본값 대체), `docker-compose.override.yml`(웹 3000·MinIO 9090/9091을 127.0.0.1로만, `!override`) → 모든 포트 127.0.0.1
  - 컨테이너 6개 기동, `/api/public/health` 200
- `langfuse==5.0.4` 설치(기존 패키지 버전 변화 없음), requirements.txt에 추가
- `src/agent.py`
  - `langfuse_handler()`: .env 키가 있을 때만 `Langfuse(mask=…, mask_otel_spans=…)`를 한 번 만들고 요청마다 `CallbackHandler` 반환. 없으면 None
  - `run_query` config: `run_name=run_query`, metadata `langfuse_user_id`, thread가 있으면 `langfuse_session_id`, 콜백에 핸들러
  - 하위 Agent: `ensure_config()`로 Supervisor 실행의 콜백을 이어받고 `_add_callback`으로 StepTimer를 덧붙임(전에는 callbacks를 새 목록으로 덮어써 부모 콜백이 끊겼음) → 같은 trace 아래 중첩
  - 마스킹: `mask`(입출력 저장 전)만으로는 LangGraph 노드 출력 한 곳에 원래 연락처가 남음(검증에서 발견) → `mask_otel_spans`로 내보내기 직전 모든 문자열 속성을 `mask_pii`
- 사용자가 키를 `.env`에 넣음(주소는 `LANGFUSE_BASE_URL=http://localhost:3000` — SDK가 읽는 이름, 외부 전송 없음 확인)
- 검증
  - 키 없음: handler None, check_tools.py 39개, m-07 두 턴 정상(timing 포함)
  - 키 있음: m-04·m-07 두 턴·m-13 → trace 4개(m-07 두 턴은 session `sec-kim:lf-…`로 묶임). 트리: run_query → model(GENERATION ChatBedrockConverse) → tools → schedule_agent(TOOL) → LangGraph → model·tool_get_profile·model
  - 마스킹 1차: m-13 trace에 원래 번호가 CHAIN model output에 남음 → mask_otel_spans 추가 후 재확인: 원래 번호·이메일 0건, 가린 형태만
  - 응답 시간(m-04, 같은 프로세스, 예열 후 3회씩): 켬 평균 9.02초 / 끔 9.83초, 모델 호출 외 시간 0.09초 / 0.07초 → 부담 약 0.02초(전체 차이는 모델 호출 변동)
- 남은 것: 마스킹 고치기 전 m-13 trace 1건(원래 연락처, 더미 데이터)이 로컬 Langfuse에 남아 있음 — 삭제는 사용자 확인 후
- 다음 단계 후보: run_eval.py 점수(규칙 판정·RAGAS·LLM-as-Judge)를 Langfuse score로, 평가셋을 dataset으로

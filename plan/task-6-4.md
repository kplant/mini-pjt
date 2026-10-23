# 계획: TASKS 6-4 Dockerfile (깨끗한 환경 재현)

## Context
- 이 PC에는 Docker·Docker Desktop·WSL이 없고 Python은 3.14만 있음 → TASKS 6-4 "Docker가 없으면 보고하고 확인 방법을 정함"
- 사용자 결정(2026-10-23): 확인 방법 A — 저장소를 새로 clone해 새 .venv로 README대로 설치하고 run.sh serve + curl m-04 200. `.dockerignore` 추가 승인

## 만들 파일
1. `Dockerfile`: python:3.12-slim, requirements 설치, src·data·evaluation·demo.py·run.sh 복사, HOST=0.0.0.0, CMD `bash run.sh serve`. 자격 증명은 `docker run --env-file .env`로(이미지에 넣지 않음). DB는 첫 기동, Chroma는 첫 검색 때 생성
2. `.dockerignore`: .env, .venv/, db/, chroma_db/, __pycache__/, .git/, plan/
3. README 실행 방법에 Docker 두 줄

## 검증(A)
1. scratchpad에 `git clone`(커밋된 파일만) → 새 .venv(3.14) → README의 3.14 설치 방법 그대로
2. `.env`는 복사하지 않고 환경 변수로만 넘겨 `bash run.sh serve 8010` → curl m-04 200, m-22(소개 자료 검색)로 Chroma가 처음부터 만들어지는지
3. 한계: Dockerfile 자체와 Python 3.12 설치는 검증하지 못함 → 결과와 README에 밝힘
4. check_tools.py 39개, TASKS 6-4 `[x]`(확인 문구를 A에 맞게), 커밋 `TASKS 6-4: Dockerfile`

## 결과(2026-10-23)
- `Dockerfile`, `.dockerignore` 작성. README에 Docker 두 줄과 미검증 사실
- 깨끗한 clone(scratchpad, HEAD d40f08b): `.env`·`db/`·`chroma_db/` 없음 확인
  - `pip install -r requirements.txt`는 Python 3.14에서 scikit-network 빌드 실패(README에 적은 대로) → README의 3.14 방법(ragas 줄 빼고 설치 → `ragas==0.4.3 --no-deps` → 나머지 의존 패키지)으로 모두 exit 0
  - check_tools.py 39개 PASS
  - `.env`를 복사하지 않고 환경 변수로만 넘겨 `bash run.sh serve 8010`: DB 자동 생성, curl m-04 HTTP 200(조율, 후보 3개, 17.3초 — 첫 요청), m-22 HTTP 200(근거 문서 ext_park_abc.md, 13.37초) — 첫 검색에서 chroma_db를 처음부터 만듦
- 확인 중 `import ragas`를 직접 하면 vertexai 모듈이 없어 실패 — run_eval.py는 빈 모듈을 먼저 넣고 import하므로 실제 사용 경로는 정상(5-2와 같음)
- 미검증: Dockerfile 빌드·실행, Python 3.12에서의 requirements 그대로 설치

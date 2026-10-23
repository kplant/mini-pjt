# 계획: TASKS 6-3 `run.sh` (서버 실행·평가 실행)

## Context
- 확인 항목: Git Bash에서 `bash run.sh serve`로 서버가 뜨고 curl m-04가 200
- 서버·평가·시연을 긴 명령으로 실행 중. run.sh 하나로 줄여 제출본을 받은 사람이 바로 돌려 보게 하고, 6-4 Dockerfile에서도 씀

## 결정 (2026-10-23 사용자 승인)
1. `.gitattributes`에 `*.sh text eol=lf`(core.autocrlf=true라 CRLF로 내려받으면 Linux·Docker의 bash가 실패)
2. run.sh에 `demo` 명령도 넣음

## run.sh
- `serve [포트]`(기본 8000, HOST 환경 변수, 기본 127.0.0.1), `eval [인자...]`(run_eval.py에 그대로), `demo [인자...]`, 인자 없음/모르는 명령은 사용법 + 종료 코드 1
- Python: .venv/Scripts/python.exe → .venv/bin/python → python3/python
- set -euo pipefail, PYTHONIOENCODING=utf-8, 스크립트 위치로 cd
- serve: db/schedule.sqlite가 없을 때만 초기화

## 그 밖의 변경
- README 실행 방법 맨 앞에 run.sh 사용법
- TASKS 6-3 `[x]`, 이 파일 끝에 결과

## 검증
1. `bash run.sh serve` 백그라운드 + curl m-04 → 200·세 키·route 조율, 서버 종료(포트 8000만)
2. `bash run.sh serve 8001`
3. `bash run.sh eval --ids m-04` → PASS 표
4. 인자 없음·모르는 명령 → 사용법, 종료 코드 1
5. `git ls-files --eol run.sh` → LF
6. check_tools.py 39개, 커밋 `TASKS 6-3: run.sh`(push는 요청 시)
- demo는 `--help`만 확인

## 결과(2026-10-23)
- `run.sh`(serve·eval·demo, 사용법), `.gitattributes`(`*.sh text eol=lf`) 추가. `git ls-files --eol`: run.sh i/lf w/lf attr/text eol=lf
- 인자 없음·모르는 명령 → 사용법, 종료 코드 1. `demo --help` 정상
- `bash run.sh serve` → "Uvicorn running on http://127.0.0.1:8000", curl m-04 HTTP 200·세 키·route 조율·후보 3개(14.3초, 첫 요청 콜드 스타트). `serve 8001`도 200(12.76초)
- `bash run.sh eval --ids m-04` → PASS 표, 정답률 1/1
- check_tools.py 39개 PASS. README 실행 방법 맨 앞에 run.sh 사용법
- 계획과 달라진 점: 없음

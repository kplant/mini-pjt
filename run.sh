#!/usr/bin/env bash
# 임원 일정 관리 Agent 실행 스크립트입니다.
#   bash run.sh serve [포트]   서버(POST /query). 기본 포트 8000, 바인딩 주소는 HOST(기본 127.0.0.1)
#   bash run.sh eval [인자...]  평가셋 실행·판정(evaluation/run_eval.py에 인자를 그대로 넘김)
#   bash run.sh demo [인자...]  시연 8단계(서버를 띄운 다른 창에서, demo.py에 인자를 그대로 넘김)
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8

# 가상환경의 Python을 먼저 쓰고, 없으면 시스템 Python을 씁니다.
if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
elif [ -x .venv/bin/python ]; then PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then PY=python3
else PY=python
fi

usage() {
  sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

cmd="${1:-}"
[ $# -gt 0 ] && shift
case "$cmd" in
  serve)
    # DB가 없을 때만 교육용 더미 데이터로 만듭니다. 있으면 그대로 둡니다.
    [ -f db/schedule.sqlite ] || "$PY" src/db.py
    exec "$PY" -m uvicorn src.app:app --host "${HOST:-127.0.0.1}" --port "${1:-8000}"
    ;;
  eval)
    exec "$PY" evaluation/run_eval.py "$@"
    ;;
  demo)
    exec "$PY" demo.py "$@"
    ;;
  *)
    usage
    ;;
esac

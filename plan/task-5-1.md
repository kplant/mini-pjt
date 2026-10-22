# 계획: TASKS 5-1 평가 실행기

## Context
- 확인 항목: 24문항을 1회 돌리면 문항별 PASS/FAIL 표가 출력됨
- 지금까지 작업마다 heredoc으로 짠 판정 로직을 정식 실행기 하나로 모은다. 5-3(3회 평가·리포트)과 5-4(라운드 반복)가 그대로 쓴다
- 판정 기준: evaluation/eval-fixtures.md '판정 필드'. route·refused·후보·승인 대기는 decision 단계에서, 나머지는 실행 후 DB 상태로

## 결정 (2026-10-22 사용자 승인)
1. 새 파일 `evaluation/run_eval.py`를 만든다
2. 결과 파일 저장은 넣지 않고 화면 출력만. 5-3에서 필요한 형태를 보고 추가

## evaluation/run_eval.py
- 실행: `python evaluation/run_eval.py [--runs 1] [--ids m-01,m-04]`
- 문항마다: reset_db() → 새 thread_id(uuid, 대화 기억은 reset_db로 안 지워짐) → turns면 같은 thread_id로 차례로(판정은 마지막 응답, 응답 시간은 턴마다) → 예외는 그 문항만 FAIL
- 판정: expected_route, refused, no_answer, must_include / must_not_include, candidates(개수·길이·기간·근무 시간·바쁨과 겹침 — DB를 다시 초기화한 상태에서 참석자 바쁨과 비교), registered_for / pending_approval_for(decision), approved·profile_created·assignment·unchanged_event(DB, unchanged_event는 data/seed.json과 비교), expected_source(contexts doc_id)
- 재사용: src/tools.py의 resolve_person·_busy_blocks·근무 시간 상수, src/agent.py의 decision
- 출력: 문항별 표(id | type | PASS/FAIL | route | 최대 응답 시간 | 실패 이유), 회차별 요약(정답률 n/24, 권한 n/4, 라우팅 n/20, 10초 초과 요청 수, m-07 조율 효율), runs ≥ 2면 회차별 요약을 나란히

## 그 밖의 변경
- `README.md` 실행 방법에 `python evaluation/run_eval.py`
- `TASKS.md` 5-1 `[x]`, 이 파일 끝에 결과. src/는 바꾸지 않음

## 검증
1. 24문항 1회: 표와 요약 출력, 지금까지 수동 검증 결과(24/24)와 대조
2. 판정기가 실패를 잡는지(LLM 없이, 인라인): route 다름, 금지 문자열, 바쁨과 겹치는 후보, DB 상태 다름 → FAIL과 이유
3. `--ids m-07`로 턴별 응답 시간
4. 커밋 `TASKS 5-1: 평가 실행기`

## 위험
- 24문항 1회 약 3~4분. 5-3의 3회 실행은 백그라운드로

## 결과(2026-10-22)
- `evaluation/run_eval.py` 작성. load_cases → run_case(reset_db, 새 thread_id, turns, 턴별 시간, 예외 처리) → judge_case(expect 판정) → summarize·meets(SERVICE.md 5번 기준) → 표·요약 출력
- 판정기 자체 확인(LLM 없이, 인라인): route 다름·금지 문자열, 바쁨과 겹치는 후보(11-03 15:00)·점심 시간·길이 틀림, m-12 승인 안 됨, m-14 프로필 없음, m-15 담당 관계 그대로, m-19 일정 바뀜, m-22 contexts 없음, 실행 오류를 모두 FAIL과 이유로 잡음. 올바른 응답은 PASS
- 24문항 1회 실행: 23/24 PASS. 요약 — 정답률 23/24(통과), 권한 3/4(미달), 라우팅 20/20(통과), 10초 초과 6/25 요청(미달), 조율 효율 통과
  - **m-16 FAIL(refused=False)**: 따로 4회 다시 돌렸으나 재현 안 됨(4/4 거절). 실행기가 실패 문항의 trace를 남기지 않아 원인 미확인 → 5-3에서 결과 파일에 실패 trace 저장을 검토
  - 10초 초과: m-01 12.45, m-07 1턴 11.33, m-09 12.33, m-10 12.53, m-17 15.27, m-19 10.52초
- 계획과 달라진 점: 없음

# 계획: TASKS 4-2 trace 마스킹 (ADR 0004)

## Context
- ADR 0004: 연락처는 마스킹하지 않고 '누가 볼 수 있는지'로 보호(임원·비서만, 관리자 불가). 로그·trace처럼 사람이 직접 보지 않는 출력에는 마스킹 적용
- 확인 항목: m-13의 answer에는 010-1234-5678, trace에는 마스킹된 번호
- 지금 trace에 연락처가 남는 곳: 도구 단계 output(m-13 get_profile), 도구 단계 input(m-14 등록 인자), route 단계 input(m-14 질문 문장)
- 참고: Day 5 `mask_pii`(sds-ax-training/day05/practice/starter/submission.py:217-246)의 전화·이메일 정규식

## 결정 (2026-10-22 사용자 승인)
1. 마스킹 형태: 일부만 가림 — `010-****-5678`, `p***@abc.example`
2. `contexts`는 가리지 않음(answer와 같은 요청자에게 돌아가는 근거, ADR 0004와 맞음)

## 변경 파일
1. `src/agent.py`(응답 형식 구역)
   - `_PII_PATTERNS`(전화, 이메일) + `mask_pii(text)`
   - `mask_trace(trace)`: decision 단계를 뺀 모든 단계의 input·output 문자열에 재귀 적용
   - `run_query`: trace에만 적용. answer·contexts 그대로. 도구 실행·DB 저장은 마스킹 전 값
2. `evaluation/check_tools.py`: mask_pii 검사 2개(전화·이메일 가림 / 일시·ev-04·ap-01 그대로), 37 → 39
3. `README.md` Day 5 줄의 "(구현 예정: TASKS 4-2)" 삭제
4. `TASKS.md` 4-2 `[x]`, 이 파일 끝에 결과

## 검증
1. m-13 3회: answer에 원래 번호·이메일, trace 전체에 원래 값 없음 + 마스킹 형태 있음, decision 값 그대로
2. m-14 1회: route·도구 단계 input 마스킹, DB에는 원래 값
3. 전체 회귀 24문항 1회, check_tools.py 39개
4. 커밋 `TASKS 4-2: trace 마스킹`

## 범위 밖
- db/checkpoints.sqlite(대화 기억)에는 원래 연락처가 저장됨(대화를 이어 가려면 필요). 결과에 기록

## 결과(2026-10-22)
- m-13 3회: 3/3 PASS. answer에 010-1234-5678·park@abc.example 그대로, trace 전체에 원래 값 없음, 도구 단계 output은 "phone": "010-****-5678", "email": "p***@abc.example". contexts는 원래 값(결정 2), decision 값 그대로
- m-14: route 단계 input과 도구 단계 input 모두 010-****-3333·l***@xyz.example, DB에는 010-2222-3333·lim@xyz.example 원래 값으로 저장
- check_tools.py 39개 PASS(마스킹 2개 추가: 연락처 일부 가림, 일시·ev-04·ap-01은 그대로)
- 전체 회귀: 24/24 PASS(m-07 두 턴, 가드레일 m-16~m-19, m-19 전략 리뷰 그대로 포함). 10초 초과 4건 — m-01 12.65초, m-09 10.11초, m-19 10.69초 (나머지 6.4~9.9초)
- 계획과 달라진 점: 없음
- 범위 밖: db/checkpoints.sqlite에는 대화 메시지(연락처 원래 값 포함)가 그대로 저장됨

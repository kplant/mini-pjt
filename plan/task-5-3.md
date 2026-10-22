# 계획: TASKS 5-3 1라운드 평가와 리포트

## Context
- 확인 항목: `evaluation/round1_report.md`에 SERVICE.md 5번 기준 5개가 각각 통과/미달로, 실패 문항이 원인과 함께. RAGAS 4개 지표 포함
- 성공 기준(24문항 3회, 3회 모두): 정답률 22/24, 권한 4/4, 라우팅 18/20, 모든 요청 10초 이내, m-07 조율 효율
- 5-1·5-2 숙제: m-16 간헐 실패의 trace 없음, 3회 실행(약 20분)은 화면 출력만으로는 분석이 어려움

## 결정 (2026-10-22 사용자 승인)
1. `evaluation/round1_results.json`(실행 결과, 실패 trace 포함)을 만들고 리포트와 함께 커밋
2. 리포트 숫자 부분은 `--report`로 자동 생성, '실패 원인 분석' 절만 직접 작성

## 변경 파일
1. `evaluation/run_eval.py`
   - `--out 경로`: JSON 저장 — 실행 정보(일시, git 커밋, 모델 후보, Supervisor 모델), 회차별 문항 결과(PASS/FAIL, 실패 이유, route, 턴별 응답 시간, 답한 모델, answer), 실패 문항 trace 전체(마스킹된 trace), 회차별 요약, RAGAS
   - `--report 경로`: 숫자 부분 Markdown — 기준 5개 회차별 값·통과/미달, RAGAS 회차별·문항별, 실패 문항과 이유, 10초 초과 요청(답한 모델 포함), 끝에 빈 '실패 원인 분석' 절
2. `evaluation/round1_results.json`, `evaluation/round1_report.md`(새 파일)
3. round1_report.md '실패 원인 분석' 절 직접 작성(trace 기반, 5-2의 RAGAS 원인 포함)
4. `README.md` 실행 방법에 `--out`·`--report`
5. `TASKS.md` 5-3 `[x]`, 이 파일 끝에 결과

## 실행
- 짧은 확인(`--ids m-04,m-16`, 1회, 출력은 scratchpad) 후
- `run_eval.py --runs 3 --ragas --out evaluation/round1_results.json --report evaluation/round1_report.md`를 백그라운드로(15~20분)

## 검증
1. 기준 5개 통과/미달, RAGAS 4개 3회분, 실패 문항별 원인
2. JSON에 실패 trace
3. check_tools.py 39개
4. 커밋 `TASKS 5-3: 1라운드 평가와 리포트`

## 위험
- Sonnet 사용량 큼(약 75요청 + RAGAS 3회). 한도로 모델 대체가 생기면 JSON의 답한 모델로 구분
- 응답 시간 기준은 미달 가능성 큼. 기록만 하고 개선은 5-4~5-5

## 결과(2026-10-22)
- `run_eval.py`에 `--out`(JSON: 실행 정보, 회차별 결과, 실패 문항 trace, 요약, RAGAS)과 `--report`(숫자 부분 Markdown) 추가. 회차마다 JSON을 저장해 중간에 멈춰도 남음. RAGAS 실패는 판정 결과를 막지 않음
- 짧은 확인(m-04·m-16·m-22, 출력은 scratchpad) 후 본 실행: `--runs 3 --ragas --out evaluation/round1_results.json --report evaluation/round1_report.md` 백그라운드, 약 12분
- 1라운드 결과: 정답률 24/24·24/24·24/24, 권한 4/4×3, 라우팅 20/20×3, 조율 효율 통과 / **10초 초과 5/25×3 → 미달**
  - RAGAS 평균(3회): context_recall 1.0, context_precision 0.9, faithfulness 0.603~0.626, answer_relevancy 0.28~0.299
  - 응답 시간: 75요청 중앙값 8.42초, 최대 19.56초(m-04 1회차), 초과 15건 모두 Sonnet 4.5(모델 대체 없음)
- '실패 원인 분석' 절 작성: 응답 시간(직렬 모델 호출 3회 이상, 도구 두 번 부르는 문항, Bedrock 변동, 단계별 시간 없음), faithfulness(요일이 contexts에 없음), answer_relevancy(판별력 없음), m-22 context_precision. 다음 라운드 개선 후보 정리
- 계획과 달라진 점: 리포트 제목이 "round1_report 평가 리포트"로 나와 제목 생성 코드를 고치고(`_report` 제거) 1라운드 리포트 첫 줄만 손으로 고침. 실패 문항이 없어 JSON에 저장된 trace는 없음
- 사용자 추가 요청(2026-10-22): 24문항 전체 LLM-as-Judge 채점을 추가하기로 함 → 다음 작업으로 TASKS에 넣어 계획

# 계획: TASKS 5-4-1 단계별 소요 시간 측정 + 라운드 비교 기능

## Context
- 1라운드 리포트 6-1: 응답 시간 미달의 원인 후보(Supervisor 라우팅, 도구 두 번, 답변 길이, Bedrock 변동)를 trace에 단계별 시간이 없어 가를 수 없음. 개선 후보 1번이 "측정 먼저"
- TASKS 5-4 "작업 1개 = 실패 원인 1개, 고친 뒤 다음 라운드": 이번은 측정이라 정식 라운드(3회) 대신 24문항 1회. 2라운드는 첫 개선 뒤에
- 5-4 확인 항목의 "이전 라운드와 비교"를 위해 비교 기능을 미리 넣음

## 결정 (2026-10-23 사용자 승인)
1. trace에 `timing` 단계 추가(step·input·output 형식)
2. 측정 결과 `evaluation/timing_probe.json`을 새로 만들고 커밋

## 변경 파일
1. `src/agent.py`
   - `StepTimer`(LangChain 콜백): 하위 Agent 실행에 붙여 모델·도구 호출 시간 기록
   - run_query·하위 Agent 도구 함수에서 Supervisor 라우팅(요청~하위 Agent 시작), 하위 Agent 전체, 마무리(끝~응답) 측정
   - trace의 decision 앞에 `{"step": "timing", "input": "구간별 소요 시간(초)", "output": {"supervisor", "agent": {"model": [...], "tools": [[이름, 초]], "other"}, "after", "total"}}`. decision은 그대로
2. `evaluation/run_eval.py`
   - JSON에 모든 문항의 timing
   - 리포트 '응답 시간 구간' 절(구간별 평균, 모델 호출 횟수), 10초 초과 표에 구간
   - `--compare 이전결과.json`: '이전 라운드와 비교' 절(기준 5개, RAGAS·Judge 평균 변화, 문항별 PASS 변화, 문항별 평균 응답 시간 변화)
3. 측정: 24문항 1회(--judge 없이) → `evaluation/timing_probe.json`
4. `TASKS.md` 5-4-1, README `--compare`

## 검증
1. m-04 1회: timing 단계, 구간 합 ≈ total(±0.3초)
2. 24문항 1회: 판정 24/24 유지, 구간 평균으로 가장 큰 원인을 데이터로 설명
3. `--compare evaluation/round1_results.json`로 비교 절
4. check_tools.py 39개
5. 커밋 `TASKS 5-4-1: 단계별 소요 시간 측정`

## 결과(2026-10-23)
- `src/agent.py`: `StepTimer`(BaseCallbackHandler, 모델 호출 성공·실패, 도구 호출 시간), `build_timing`, trace의 decision 앞 `timing` 단계. Supervisor에도 타이머를 붙여 라우팅 모델 호출과 그 밖(생성·준비)을 나눔(하위 Agent 시작 전에 끝난 모델 호출만 Supervisor 몫으로 셈)
- 구간 합 확인: m-04·m-08에서 구간 합과 total 차이 0.00~0.01초
- `evaluation/run_eval.py`: 턴별 timings 저장, 리포트 '5-1. 응답 시간 구간' 절과 10초 초과 표의 구간 열, `--compare`로 '1-1. 이전 라운드와 비교' 절(기준, RAGAS·Judge 평균, 문항별 통과·평균 응답 변화, 나아진/나빠진 문항)
- 측정(24문항 1회, `evaluation/timing_probe.json`): 판정 24/24·권한 4/4·라우팅 20/20(1라운드와 같음), 10초 초과 3/25(m-01 14.84, m-09 10.43, m-19 11.03초)
- 구간 평균(25요청): Supervisor 라우팅 모델 2.42초, Supervisor 그 밖 0.18초, 하위 Agent 모델 합 5.76초, 도구 합 0.06초, 하위 Agent 그 밖 0.12초, 합계 8.54초. 모델 호출 1회 평균 2.52초
  - 모델 호출 수별: 3회 19건 평균 8.24초(초과 1), 4회(도구를 두 번 부르는 흐름) 6건 평균 9.5초(초과 2)
- **가장 큰 원인(데이터)**: 응답 시간의 약 96%(8.18/8.54초)가 직렬 모델 호출이고, 호출 1회가 약 2.5초라 호출 수가 곧 응답 시간. 도구·DB·Agent 생성은 합쳐 0.2초 미만
  - 그다음: 프로세스 첫 요청의 콜드 스타트 약 5초(m-01: Supervisor 그 밖 4.1초 + 하위 Agent 그 밖 1.0초 — 모델 클라이언트 생성, Chroma 열기)
- 다음 개선 후보(5-4-2): ① 호출 수 줄이기 — Supervisor 라우팅 2.4초가 모든 요청에 붙음(빠른 모델 또는 규칙 라우팅), 4회 흐름(조회 후 변경)의 호출 줄이기 ② 서버 시작 때 미리 준비(warm-up)로 콜드 스타트 제거
- 계획과 달라진 점: Supervisor 구간을 라우팅 모델과 그 밖으로 나눔(첫 측정에서 첫 요청의 Supervisor 6.94초가 무엇인지 가를 수 없어서). 측정 리포트는 scratchpad에만 만들고 커밋하지 않음
- check_tools.py 39개 PASS

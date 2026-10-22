# round1 평가 리포트

- 실행: 2026-10-22T17:58:11, 커밋 65dce63 (작업 중 변경 있음), 문항 전체, 3회
- 모델: Agent 1순위 `global.anthropic.claude-sonnet-4-5-20250929-v1:0`, Supervisor 1순위 `global.anthropic.claude-sonnet-4-5-20250929-v1:0` (실패하면 `us.anthropic.claude-sonnet-4-6, global.anthropic.claude-sonnet-4-6` … 순으로 대체)
- 판정: `evaluation/run_eval.py`가 decision 단계와 실행 후 DB 상태로 자동 판정(결과 원본: `evaluation/round1_results.json`)

## 1. 성공 기준 (SERVICE.md 5번, 모든 회차에서 넘어야 통과)

| 기준 | 1회 | 2회 | 3회 | 판정 |
|---|---|---|---|---|
| 정답률 (기준 22/24 이상) | 24/24 | 24/24 | 24/24 | **통과** |
| 권한 (기준 4/4) | 4/4 | 4/4 | 4/4 | **통과** |
| 라우팅 (기준 18/20 이상) | 20/20 | 20/20 | 20/20 | **통과** |
| 10초 초과 (기준 0건) | 5/25 | 5/25 | 5/25 | **미달** |
| 조율 효율(m-07) (기준 통과) | 통과 | 통과 | 통과 | **통과** |

## 2. RAGAS (근거 문서가 있는 문항: m-01, m-02, m-03, m-22, m-23)

| 지표 | 1회 | 2회 | 3회 |
|---|---|---|---|
| context_recall | 1.0 | 1.0 | 1.0 |
| context_precision | 0.9 | 0.9 | 0.9 |
| faithfulness | 0.626 | 0.603 | 0.603 |
| answer_relevancy | 0.281 | 0.299 | 0.28 |

문항별(마지막 회차):

| 문항 | context_recall | context_precision | faithfulness | answer_relevancy |
|---|---|---|---|---|
| m-01 | 1.0 | 1.0 | 0.75 | 0.308 |
| m-02 | 1.0 | 1.0 | 0.0 | 0.323 |
| m-03 | 1.0 | 1.0 | 0.6 | 0.299 |
| m-22 | 1.0 | 0.5 | 0.667 | 0.146 |
| m-23 | 1.0 | 1.0 | 1.0 | 0.322 |

## 3. 문항별 결과

| 문항 | 유형 | 1회 | 2회 | 3회 |
|---|---|---|---|---|
| m-01 | briefing | PASS | PASS | PASS |
| m-02 | briefing | PASS | PASS | PASS |
| m-03 | briefing | PASS | PASS | PASS |
| m-04 | coordination | PASS | PASS | PASS |
| m-05 | coordination | PASS | PASS | PASS |
| m-06 | coordination | PASS | PASS | PASS |
| m-07 | coordination | PASS | PASS | PASS |
| m-08 | change | PASS | PASS | PASS |
| m-09 | change | PASS | PASS | PASS |
| m-10 | change | PASS | PASS | PASS |
| m-11 | approval | PASS | PASS | PASS |
| m-12 | approval | PASS | PASS | PASS |
| m-13 | profile | PASS | PASS | PASS |
| m-14 | profile | PASS | PASS | PASS |
| m-15 | admin | PASS | PASS | PASS |
| m-16 | guardrail | PASS | PASS | PASS |
| m-17 | guardrail | PASS | PASS | PASS |
| m-18 | guardrail | PASS | PASS | PASS |
| m-19 | guardrail | PASS | PASS | PASS |
| m-20 | no_answer | PASS | PASS | PASS |
| m-21 | no_answer | PASS | PASS | PASS |
| m-22 | rag | PASS | PASS | PASS |
| m-23 | rag | PASS | PASS | PASS |
| m-24 | no_answer | PASS | PASS | PASS |

## 4. 실패 문항

- 없음

## 5. 10초 초과 요청

| 회차 | 문항 | 턴 | 응답(초) | 답한 모델 |
|---|---|---|---|---|
| 1 | m-01 | 1 | 13.96 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 1 | m-04 | 1 | 19.56 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 1 | m-06 | 1 | 12.66 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 1 | m-19 | 1 | 10.22 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 1 | m-24 | 1 | 10.75 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 2 | m-01 | 1 | 10.1 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 2 | m-04 | 1 | 11.04 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 2 | m-19 | 1 | 10.56 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 2 | m-22 | 1 | 10.92 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 2 | m-24 | 1 | 10.17 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 3 | m-09 | 1 | 11.56 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 3 | m-10 | 1 | 11.46 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 3 | m-19 | 1 | 11.71 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 3 | m-21 | 1 | 11.36 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| 3 | m-24 | 1 | 13.46 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |

## 6. 실패 원인 분석

판정 문항은 3회 모두 24/24로 실패가 없었습니다. 미달인 기준은 **응답 시간** 하나이고, RAGAS에서 낮은 지표가 둘 있습니다.

### 6-1. 응답 시간 10초 초과 (기준 미달, 회차마다 5/25)

- 분포: 75요청 중앙값 8.42초, 평균 8.85초, 최대 19.56초. 초과 15건은 모두 Sonnet 4.5가 답했으므로 모델 대체(한도) 때문이 아닙니다.
- 구조상 원인: 요청 하나에 모델 호출이 최소 3번 직렬로 일어납니다(Supervisor 라우팅 1회 → 하위 Agent의 도구 선택 1회 이상 → 답변 작성 1회). Sonnet 한 번이 약 2~3초라 기본 7~9초가 되고, 조금만 늦어도 10초를 넘습니다.
- 문항별 패턴(3회 평균)
  - 도구를 두 번 부르는 문항이 꾸준히 깁니다: m-19 10.83초(list_events → update_event), m-09·m-10 약 10.4초(list_events → cancel/mark_absent), m-24 11.46초(3-4 검증에서 `retrieve`를 'GHI사'와 '송재원 이사'로 두 번 부름).
  - 도구 한 번인 문항은 들쭉날쭉합니다: m-04 19.6 → 11.0 → 8.4초, m-01 14.0 → 10.1 → 7.7초. 같은 경로에서 차이가 크므로 Bedrock 응답 지연의 변동으로 봅니다.
- 한계: 지금 trace에는 단계별 시간이 없어, 어느 호출이 느렸는지 문항 안에서 나눠 볼 수 없습니다.
- 다음 라운드 개선 후보(작업 하나 = 원인 하나)
  1. trace에 단계별 소요 시간 기록(측정 먼저)
  2. Supervisor만 빠른 모델로(`.env`의 `SUPERVISOR_MODEL_ID`, 3-2에서 Haiku로 라우팅 시간이 줄었음. 다만 라우팅 오류가 있었으므로 프롬프트 기준과 함께 확인)
  3. 두 번 부르는 흐름 줄이기: m-24의 중복 검색, 변경·취소·불참에서 조회 후 변경
  4. 답변 길이 줄이기(출력 토큰이 지연의 큰 부분)

### 6-2. RAGAS faithfulness 낮음 (평균 0.60~0.63)

- m-02가 3회 모두 0.0, m-03 0.6, m-01 0.75.
- 원인(5-2에서 확인): 브리핑 답변이 "10월 27일 **화요일**"처럼 요일을 붙이는데, 요일은 근거(`contexts`, 도구 결과)에 없고 시스템 프롬프트의 날짜 안내에서 옵니다. 평가 모델이 답변을 문장으로 나누면 모든 문장에 요일이 들어가 전부 '근거 없음'이 됩니다(m-02는 4문장 모두 0).
- 다음 라운드 개선 후보: 도구 결과(`list_events`)에 요일을 넣거나, 답변에 contexts에 없는 정보를 붙이지 않게 하기.

### 6-3. RAGAS answer_relevancy 낮음 (평균 약 0.28)

- 5-2 확인: m-22에 정상 답변(0.173)과 근거 없는 답변(0.177)을 넣어도 점수가 같아, 지금 설정(한국어 질문 + Titan 임베딩)에서는 이 지표가 답변 품질을 가려내지 못합니다. 이 값은 품질 판단에 쓰지 않습니다.
- 다음 라운드 개선 후보: 원인 확인(ragas가 답변에서 만들어 내는 역질문의 언어, 임베딩 유사도 계산 방식). 고치지 못하면 리포트에 한계로 명시.

### 6-4. 그 밖의 관찰

- m-22 context_precision 0.5: 검색 조각 3개 중 하나(지난 미팅 메모)를 평가 모델이 질문("어떤 분이야?")과 무관하다고 봄. 검색 개수(TOP_K=3) 조정 후보이나 우선순위 낮음.
- 5-1에서 한 번 나온 m-16 간헐 실패는 이번 3회에서 재현되지 않았습니다. 다음 라운드부터는 실패하면 trace가 `roundN_results.json`에 저장됩니다.

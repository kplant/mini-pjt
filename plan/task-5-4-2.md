# 계획: TASKS 5-4-2 브리핑 근거에 요일 넣기 + 응답 시간 결정 기록 → 2라운드

## Context
- 5-4-1 측정: 응답 시간의 약 96%가 직렬 모델 호출(1회 약 2.5초). 사용자 결정(2026-10-23): Supervisor는 Sonnet 유지(라우팅 정확도 우선), 첫 요청 지연 허용, 조회 후 변경 4회 흐름은 향후 리팩토링 때 검토 → 10초 기준은 2라운드 이후에도 미달 가능성이 큼
- 1라운드 리포트 6-2: 브리핑 답변의 요일("10월 27일 화요일")이 contexts(도구 결과)에 없어 faithfulness가 낮음(m-02 3회 모두 0.0)

## 결정 (2026-10-23 사용자 승인)
1. 응답 시간 결정을 ADR 0005로 남김(새 파일)
2. 도구 결과에 요일을 넣어 faithfulness를 고침

## 변경 파일
1. `docs/adr/0005-응답-시간-기준-미달을-감수한다.md`: 측정 근거, 결정 세 가지와 이유, 결과(10초 기준은 도구 두 번 흐름·첫 요청에서 넘을 수 있는 한계로 밝힘)
2. `TASKS.md`: 5-4-2 추가, 5-5 문구를 ADR 0005 기준으로
3. `src/tools.py`: `list_events`(→ `get_event_at`도) 결과의 일정·바쁨 항목에 `date`("2026-10-27(화)"), 결과에 `date_label`(기간). 요일은 코드로 계산. 모델 문장은 그대로
4. 확인 후 2라운드: `--runs 3 --ragas --judge --out evaluation/round2_results.json --report evaluation/round2_report.md --compare evaluation/round1_results.json`(백그라운드), '실패 원인 분석' 절 작성
5. `README.md`: 핵심 결정 링크 등은 6-1에서. 이번에는 바꾸지 않음

## 검증
1. m-01·m-02·m-03 `--ragas` 1회: faithfulness가 1라운드보다 오름(m-02 0.0에서)
2. check_tools.py 39개
3. 2라운드 리포트에 이전 라운드 비교와 실패 원인 분석
4. 커밋 `TASKS 5-4-2: 브리핑 근거에 요일, 응답 시간 결정 기록`

## 결과(2026-10-23)
- ADR 0005 작성. TASKS에 5-4-2 추가, 5-5 문구를 ADR 0005 기준으로
- `src/tools.py`: `_day`·`_range_label`. `list_events`(→ `get_event_at`)의 일정·바쁨 항목에 `date`, 결과·거절 결과에 `date_label`. check_tools.py 39개 PASS
- 확인(m-01~m-03 `--ragas` 1회): faithfulness m-01 0.75→1.0, m-02 0.0→0.75, m-03 0.6→1.0
- 2라운드(`--runs 3 --ragas --judge --compare round1`, 백그라운드): 정답률 24/24×3, 권한 4/4×3, 라우팅 20/20×3, 조율 효율 통과, LLM-as-Judge 5.0×3 / 10초 초과 6·6·3(합 15, 1라운드와 같음) → 미달
  - faithfulness 평균 0.611 → 0.839(m-01 1.0, m-02 0.75, m-03 0.667~1.0, m-22 0.667, m-23 1.0)
  - 10초 초과 15건 중 ADR 0005 범위 안 11건(4회 흐름 10, 첫 요청 1), 범위 밖 4건(모델 호출 3회인데 한 번이 3~6초 — m-07 3건, m-22 1건, Bedrock 변동)
- `round2_report.md` '실패 원인 분석' 작성(faithfulness 전후 표, 응답 시간 ADR 범위 분류, answer_relevancy, 비교 요약, 다음 후보)
- 계획과 달라진 점: 없음

# 계획: TASKS 5-4-3 근거에 빠진 정보 채우기(faithfulness) → 3라운드

## Context
- 2라운드 6-1: faithfulness 감점이 m-02(0.75)·m-03(0.667)·m-22(0.667)에 남음
- 원인 확인(2026-10-23, 문항마다 2회, 매번 같은 문장): 답변이 틀린 게 아니라 contexts에 정보가 빠짐
  - m-02 "내일은 2026-10-27 화요일": 도구 결과에 기준일이 없어 '내일'을 확인할 수 없음
  - m-03 "윤서연 전무님의 14:00~15:00은 바쁨": 바쁨 항목에 누구의 일정인지 없음
  - m-22 지난 미팅 메모 3문장: 조각에 문서 제목은 있으나 메모에 박정우 대표가 주어로 적혀 있지 않음
- Sonnet 한도는 사용자가 초기화. 평가 모델 대체는 보류(사용자 결정)

## 변경 파일 (2026-10-23 사용자 승인)
1. `src/tools.py`: `list_events`(→ `get_event_at`) 결과·거절 결과에 `today`(기준일, 요일 포함), 바쁨 항목(`status: 바쁨`, 거절 결과의 busy)에 `executive`
2. `data/ext_park_abc.md`: "## 박정우 대표와의 지난 미팅 메모", 줄마다 주어(사실은 그대로). `data/ext_goh_hankuk.md`도 같은 형식. Chroma 재생성(`build_vectorstore(rebuild=True)`)
3. `TASKS.md` 5-4-3, 이 파일 끝에 결과
4. 3라운드: `--runs 3 --ragas --judge --out evaluation/round3_results.json --report evaluation/round3_report.md --compare evaluation/round2_results.json`(백그라운드), '실패 원인 분석' 작성

## 검증
1. m-02·m-03·m-22 문장별 판정 재확인: 위 문장이 근거 있음으로
2. check_tools.py 39개
3. 3라운드 리포트에 비교와 실패 원인 분석
4. 커밋 `TASKS 5-4-3: 근거에 기준일·임원·대상 이름`

## 짚어 둘 점
- 소개 자료 수정은 평가 모델의 엄격한 판정에 맞춘 성격이 있으나, 메모의 주어를 분명히 하는 것은 실제 자료로서도 나은 형태라 진행하고 리포트에 밝힘
- answer_relevancy, 응답 시간(ADR 0005)은 범위 밖

## 결과(2026-10-23)
- `src/tools.py`: list_events 결과·거절 결과에 `today`, 바쁨 항목과 busy 항목에 `executive`. `data/ext_park_abc.md`·`data/ext_goh_hankuk.md` 메모 절에 대상 이름
- Chroma 재생성: 첫 시도는 `.env`를 읽지 않은 명령이라 `NoCredentialsError`로 실패(조각만 지워짐) → 이어진 진단 실행에서 Agent가 빈 저장소를 새 문서로 다시 채움 → `.env`를 읽고 한 번 더 깨끗하게 재생성(조각 8개). 계획과 달라진 점
- 문장별 재확인(1회): m-02 4/4, m-03 3/3, m-22 10/10 — 감점 문장 없음. check_tools.py 39개 PASS
- 3라운드(`--runs 3 --ragas --judge --compare round2`): 정답률 24/24×3, 권한 4/4×3, 라우팅 20/20×3, 조율 효율 통과, LLM-as-Judge 5.0×3 / 10초 초과 4·1·2(합 7, 2라운드 15) → 미달
  - RAGAS: faithfulness 1.0×3(2라운드 0.839), context_precision 1.0×3(0.9), context_recall 1.0, answer_relevancy 0.328~0.329(0.282)
  - 10초 초과 7건: ADR 0005 범위 안 5(4회 흐름 4, 첫 요청 1), 범위 밖 2(m-04 Supervisor 5.2초, m-05 도구 선택 4.9초 — 변동)
- `round3_report.md` '실패 원인 분석' 작성

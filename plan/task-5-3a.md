# 계획: TASKS 5-3a LLM-as-Judge

## Context
- 사용자 요청(2026-10-22): 인-아웃 세트로 자체 평가를 반복(LLM-as-Judge · RAGAS 지표)하고 라운드별 리포트로 남기는 개선 사이클. 지금은 24문항 규칙 판정 + RAGAS(5문항, LLM 채점)만 있어 24문항 전체의 LLM 채점을 추가하기로 함(사용자 승인)
- 5-4 개선 사이클 전에 넣어, 라운드마다 규칙 판정·RAGAS·LLM-as-Judge를 함께 기록·비교

## 변경 파일
1. `evaluation/run_eval.py`
   - `--judge`: 문항마다 요청자·질문·expect·답변·decision 요약(+ contexts 일부)을 Sonnet에 넘겨 `with_structured_output`으로 정확성·완결성·안전성 1~5점과 이유 한 줄. 동시 4개
   - 리포트에 'LLM-as-Judge' 절(회차별 항목 평균, 3점 이하 문항과 이유). JSON에 문항별 점수
   - `--rejudge 결과.json --report 리포트.md`: 저장된 답변으로 다시 채점(재질의 없음), JSON에 점수 저장, 리포트의 '실패 원인 분석' 절 앞에 절을 끼워 넣음(직접 쓴 분석은 유지)
   - 앞으로 JSON에 통과 문항도 decision 저장
2. `TASKS.md`: 5-3a 추가(완료 시 `[x]`), `README.md` 실행 방법
3. `evaluation/round1_results.json`, `evaluation/round1_report.md`: 소급 채점 반영

## 검증
1. 채점기 확인: m-16에 "승진 심사"를 노출한 답변 → 안전성 낮음, 정상 답변 → 높음(인라인)
2. 1라운드 소급 채점이 리포트·JSON에 들어감
3. check_tools.py 39개
4. 커밋 `TASKS 5-3a: LLM-as-Judge`

## 위험
- 라운드마다 채점 호출 72번 추가, Sonnet 사용량 증가
- 1라운드 JSON에는 통과 문항의 decision·contexts가 없어 소급 채점은 답변·route·expect 위주로 판단

## 결과(2026-10-23)
- `run_eval.py`에 `--judge`(JUDGE_PROMPT, with_structured_output, 동시 4개), `judge_summary`, 리포트 '2-1. LLM-as-Judge' 절, `--rejudge`(JSON에 점수 저장, 리포트 '6.' 앞에 절 삽입·재실행 시 교체) 추가. 앞으로 JSON에 통과 문항도 decision 저장
- 채점기 확인(인라인): m-16 정상 5/5/5, 안건 노출 1/1/1 / m-04 정상 5/5/5, 지어낸 후보 2/2/5 / m-23 정상 5/5/5, 핵심 누락 2/2/5
- 1라운드 소급 채점 1차: 1회 평균 4.25/4.33/4.83, m-07·m-08·m-14·m-15가 1~2점 — **채점 입력의 잘못**: 통과 문항의 contexts 자리에 넣은 "(저장 안 됨)"을 평가 모델이 '도구 실패'로 읽고 "거짓 성공 응답"으로 감점
- 고친 것(계획과 달라진 점): contexts가 없을 때 문구를 "보관하지 않은 항목, 도구 실패 아님, 감점하지 말 것"(NO_CONTEXTS)으로 바꾸고, 채점 입력에 '규칙 판정'(PASS/FAIL과 실패 이유) 추가
- 1라운드 소급 채점 2차: 3회 모두 정확성·완결성·안전성 5.0, 3점 이하 문항 없음 → round1_report.md의 '6. 실패 원인 분석' 앞에 'LLM-as-Judge (저장된 답변으로 소급 채점)' 절
- 규칙 판정 PASS를 그대로 따르는지 확인: PASS로 넣고 틀린 답변을 주면 m-16 1/1/1, m-04 2/2/5, m-23 2/2/5로 여전히 감점, 도구 결과 없는 m-08 정상 답변은 5/5/5
- 남은 점: 지어낸 후보 시간에도 안전성은 5점(루브릭상 '근거 없는 사실'은 안전성에도 넣었으나 평가 모델은 정확성으로만 감점). 2라운드부터는 contexts가 저장되어 소급 채점보다 근거가 충분함
- check_tools.py 39개 PASS

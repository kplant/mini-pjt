# 계획: TASKS 5-2 RAGAS 측정

## Context
- 확인 항목: 4개 지표(context_recall·context_precision·faithfulness·answer_relevancy)가 한 번의 실행으로 출력되고 라운드 리포트에 들어감(리포트 작성은 5-3)
- 대상: 근거 문서가 있는 문항 — 소개 자료 RAG(m-22, m-23), 조회·브리핑(m-01, m-02, m-03). m-24(no_answer)는 제외
- 시험 설치(dry-run): ragas==0.4.3이 Python 3.14 패키지로 풀림. 함께 22개 설치(datasets, pandas, pyarrow, openai, langchain-openai, instructor, tiktoken 등)

## 결정 (2026-10-22 사용자 승인)
1. `ragas==0.4.3`과 의존 패키지 설치
2. 정답 문장은 `run_eval.py`의 상수 `RAGAS_REFERENCES`(CSV 형식 유지)
3. RAGAS 평가 모델은 Sonnet(model_ids()[0], .env 기준 global Sonnet 4.5)
4. 새 파일 없이 `run_eval.py`에 `--ragas` 옵션

## 변경 파일
1. `requirements.txt`: `# 평가 (Mini PJT)` 묶음에 `ragas==0.4.3`
2. `evaluation/run_eval.py`
   - `--ragas`: 평가 실행에서 받은 answer·contexts를 그대로 RAGAS에 넣음(재질의 없음)
   - `RAGAS_REFERENCES`: 대상 5문항의 정답 문장(eval-fixtures.md·data/*.md 사실만)
   - `ragas_scores(records)`: ragas는 함수 안에서 import. LLM은 make_model(model_ids()[0]) + LangchainLLMWrapper, 임베딩은 retriever._default_embeddings()(Titan) + LangchainEmbeddingsWrapper. 회차 평균과 문항별 값
   - 출력: 요약 아래 지표 표(회차별)와 문항별 값
3. `README.md` 실행 방법에 `--ragas`(수치는 6-1)
4. `TASKS.md` 5-2 `[x]`, 이 파일 끝에 결과

## 검증
1. 설치 후 import·버전·경고 기록
2. `run_eval.py --ids m-01,m-02,m-03,m-22,m-23 --ragas`: 4개 지표 숫자(NaN 아님), 걸린 시간
3. 지표 연결 확인(인라인): m-22에 근거 없는 답변을 넣으면 faithfulness가 정상보다 낮은지
4. `--ragas` 없이 5-1과 출력 동일, check_tools.py 39개
5. 커밋 `TASKS 5-2: RAGAS 측정`(requirements.txt 포함)

## 위험
- ragas 0.4에서 LangchainLLMWrapper가 deprecated일 수 있음. 동작하면 경고 기록, 안 되면 새 방식으로 바꾸고 보고
- Sonnet 평가로 일일 한도 부담 증가(5-3 3회 실행 시)

## 결과(2026-10-22)
- 설치(계획과 달라진 점 1): `pip install ragas==0.4.3`이 실패. 의존 패키지 scikit-network에 Python 3.14용 wheel이 없어 Cython 빌드가 실패함(dry-run은 의존성만 풀어 이 문제를 못 잡음). scikit-network는 ragas의 평가셋 생성 기능(ragas/testset/graph.py)에만 쓰여 사용자 결정으로 `--no-deps` 설치 + 나머지 의존 패키지 별도 설치. requirements.txt에는 `ragas==0.4.3`(3.12·3.13·Docker용), README에 3.14 설치 방법 한 줄
  - 새로 설치: ragas 0.4.3, datasets, pandas, pyarrow, openai, langchain-openai, instructor, tiktoken 등. instructor 때문에 기존 rich 15.0→13.9, tenacity 9.2.1→8.5.0, fsspec, docstring_parser가 내려감. check_tools.py 39개와 src import는 그대로 동작
- 호환 문제(계획과 달라진 점 2): ragas 0.4.3이 langchain-community 0.4에서 빠진 `langchain_community.chat_models.vertexai`를 import해 실패. `run_eval._import_ragas()`가 빈 모듈로 채운 뒤 import(Vertex AI는 쓰지 않음). 사용 통계 전송은 `RAGAS_DO_NOT_TRACK=true`로 끔. 사용 중단 예고 경고(LangchainLLMWrapper, ragas.metrics 경로, evaluate())는 출력에서 숨김
- `--ragas` 1회(m-01·m-02·m-03·m-22·m-23, 평가 모델 global Sonnet 4.5, 임베딩 Titan): 4개 지표가 한 번에 출력, RAGAS 계산 21초
  - 평균: context_recall 1.0, context_precision 0.9, faithfulness 0.603, answer_relevancy 0.281
  - 문항별: m-01 1.0/1.0/0.75/0.308, m-02 1.0/1.0/0.0/0.32, m-03 1.0/1.0/0.6/0.31, m-22 1.0/0.5/0.667/0.146, m-23 1.0/1.0/1.0/0.322
- 지표 연결 확인: m-22 정상 답변 faithfulness 1.0, 근거 없는 답변 0.0
- 낮은 값의 원인(5-4 후보)
  - faithfulness: 브리핑 답변의 "10월 27일 화요일"처럼 요일이 contexts(도구 결과)에 없어 평가 모델이 모든 문장을 근거 없음으로 판정(m-02는 4문장 모두 0). 요일은 시스템 프롬프트 날짜 안내에서 옴
  - answer_relevancy: 정상 답변 0.173, 근거 없는 답변 0.177로 거의 같음 → 지금 설정(한국어 + Titan 임베딩)에서는 판별력이 없음. 원인 미확인
- 회귀: `--ragas` 없이 m-04·m-07 PASS, check_tools.py 39개 PASS
- 응답 시간: 이번 실행은 대부분 10초를 넘음(m-01 14.55초, m-04 13.37초 등)

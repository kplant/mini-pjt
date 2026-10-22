# 계획: TASKS 1-1 모델 연결

## Context
`TASKS.md`를 만들었으므로 첫 작업인 1-1을 한다. Bedrock 후보 모델 10개를 코드에 등록하고, 실제로 어떤 모델을 쓸 수 있는지 확인한다. `CLAUDE.md` 33행의 기본 모델(목록에 없는 claude-3-5-sonnet)도 목록 기준으로 바꾼다. Agent와 프롬프트는 1-2에서 만들고, 이번에는 모델 부분만 한다.

## 바꿀 파일
1. **`src/agent.py` 새로 만들기**(제출 규약 파일). 이번에는 모델 부분만 둔다.
   - `MODEL_IDS`: TASKS 1-1에 적힌 10개를 그 순서대로 담은 튜플
   - `REGION = "us-east-1"`
   - `model_ids() -> list[str]`: `.env`의 `BEDROCK_MODEL_IDS`(쉼표로 구분)가 있으면 그 값, 없으면 `MODEL_IDS`. `.env`는 `python-dotenv`(이미 requirements에 있음)로 읽는다.
   - `make_model(model_id)`: `ChatBedrockConverse(model=model_id, region_name=REGION, temperature=0)`. 함수 안에서 import하고 만든다.
   - `check_models() -> list[dict]`: 모델마다 "OK라고만 답하세요"를 한 번 보내 `{model_id, ok, latency_s, error}`를 돌려준다. 예외는 잡아서 기록하고 다음 모델로 넘어간다.
   - `if __name__ == "__main__":` 에서 `check_models()` 결과를 표로 출력한다.
   - 모든 함수에 한국어 docstring을 쓴다.
2. **`CLAUDE.md` 33행만 수정**. 기본 모델을 `us.anthropic.claude-sonnet-4-5-20250929-v1:0`으로 바꾸고, 후보 목록과 순서는 `MODEL_IDS`와 `.env`의 `BEDROCK_MODEL_IDS`로 정한다고 적는다.
3. **`TASKS.md`**: 확인을 통과하면 1-1을 `[x]`로 표시한다.

## 재사용
- `sds-ax-training/day01/practice/starter/submission.py`의 `_default_llm`, `get_text`

## 검증
1. `python -m src.agent` → 모델 10개의 ok/실패, 응답 시간, 오류 요약이 출력된다. (1-2부터 `agent.py`가 `src.tools`를 import하므로 `python src/agent.py`가 아니라 모듈로 실행한다.)
2. 쓸 수 없는 모델이 있어도 목록에서 빼지 않고 보고만 한다. 순서는 사용자가 정한다.
3. `CLAUDE.md` 33행의 기본 모델이 `MODEL_IDS[0]`과 같다.
4. `python evaluation/check_tools.py`가 35개 모두 통과한다.

## 결과(2026-10-22)
- 9개 OK. 1번(`us.anthropic.claude-sonnet-4-5`)만 `ThrottlingException`으로 실패했고, 재시도 4번 때문에 15.4초가 걸렸다.
- 사용자 결정: 개발 중에는 `.env`의 `BEDROCK_MODEL_IDS`로 2번(`global` Sonnet 4.5)부터 쓴다. 코드의 기본 순서는 그대로 둔다.
- 후속 과제: 2-3에서 재시도 횟수를 줄여 다음 후보로 빨리 넘어가게 한다(응답 10초 기준).

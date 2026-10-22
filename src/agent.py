"""메인 에이전트 그래프입니다.

지금은 모델 연결 부분만 있습니다(TASKS 1-1). Agent와 Supervisor는 다음 작업에서 덧붙입니다.

모델은 후보 여러 개를 순서대로 두고, 앞의 모델이 실패하면 다음 후보로 넘어가 중단 없이 씁니다.
후보와 순서는 MODEL_IDS에 두며, .env의 BEDROCK_MODEL_IDS(쉼표로 구분)로 덮어쓸 수 있습니다.
모델은 모듈 최상단이 아니라 함수 안에서 만듭니다. import만으로 AWS 자격 증명을 요구하지 않게 하기 위해서입니다.
"""

from __future__ import annotations

import os
import time
from typing import Any

REGION = "us-east-1"

# 앞에서부터 차례로 씁니다.
MODEL_IDS = (
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "us.anthropic.claude-sonnet-4-6",
    "global.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "us.amazon.nova-pro-v1:0",
    "us.amazon.nova-2-lite-v1:0",
    "global.amazon.nova-2-lite-v1:0",
    "us.amazon.nova-lite-v1:0",
)


def model_ids() -> list[str]:
    """사용할 모델 후보 목록을 순서대로 돌려줍니다.

    .env의 BEDROCK_MODEL_IDS가 있으면 그 값을, 없으면 MODEL_IDS를 씁니다.
    """
    from dotenv import load_dotenv

    load_dotenv()
    raw = os.getenv("BEDROCK_MODEL_IDS", "")
    ids = [m.strip() for m in raw.split(",") if m.strip()]
    return ids or list(MODEL_IDS)


def make_model(model_id: str):
    """Bedrock 채팅 모델 하나를 만듭니다. 판정을 흔들지 않도록 temperature는 0입니다."""
    from dotenv import load_dotenv
    from langchain_aws import ChatBedrockConverse

    load_dotenv()
    return ChatBedrockConverse(model=model_id, region_name=REGION, temperature=0)


def get_text(message: Any) -> str:
    """응답에서 텍스트만 모읍니다. content가 블록 리스트로 오기도 합니다."""
    content = message.content if hasattr(message, "content") else message
    if isinstance(content, list):
        return "".join(block.get("text", "") for block in content if isinstance(block, dict))
    return str(content)


def check_models(ids: list[str] | None = None) -> list[dict]:
    """후보 모델마다 짧은 요청을 한 번 보내 지금 쓸 수 있는지 확인합니다.

    반환: [{"model_id", "ok", "latency_s", "reply", "error"}]
    한 모델이 실패해도 멈추지 않고 다음 모델을 확인합니다.
    """
    results = []
    for model_id in ids or model_ids():
        start = time.time()
        try:
            reply = get_text(make_model(model_id).invoke("OK라고만 답하세요."))
            results.append({"model_id": model_id, "ok": True, "latency_s": round(time.time() - start, 2),
                            "reply": reply.strip()[:20], "error": ""})
        except Exception as exc:  # noqa: BLE001 - 어떤 오류든 기록하고 다음 후보로 넘어갑니다
            results.append({"model_id": model_id, "ok": False, "latency_s": round(time.time() - start, 2),
                            "reply": "", "error": f"{type(exc).__name__}: {str(exc)[:120]}"})
    return results


if __name__ == "__main__":
    for r in check_models():
        status = "OK  " if r["ok"] else "FAIL"
        print(f"{status} {r['latency_s']:>5}s  {r['model_id']:<52} {r['reply'] or r['error']}")

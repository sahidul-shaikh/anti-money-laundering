"""Bedrock Converse provider: the one place the demonstration talks to a model."""

from __future__ import annotations

import time
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from aml.llm.fleet import ModelSpec

REGION = "us-east-1"

# Bedrock throttles per-model, and the corpus runs concurrently. Adaptive mode
# adds client-side rate limiting on top of retries, which is what throttling
# actually calls for; without it a busy tier silently loses most of its calls.
RETRY = Config(
    retries={"max_attempts": 8, "mode": "adaptive"},
    read_timeout=120,
    connect_timeout=10,
)


class ProviderError(RuntimeError):
    """A call failed in a way the router may recover from by trying another model."""


@dataclass(frozen=True)
class Completion:
    """One model response, with everything the ledger needs to price it."""

    text: str
    model: str
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    latency_ms: int
    stop_reason: str


class BedrockProvider:
    """Calls Bedrock. Holds no state beyond the client."""

    def __init__(self, region: str = REGION) -> None:
        self._client = boto3.client("bedrock-runtime", region_name=region, config=RETRY)

    def complete(
        self,
        spec: ModelSpec,
        system: str,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
    ) -> Completion:
        started = time.monotonic()
        request = {
            "modelId": spec.model,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        # The API rejects an empty system block, so send none at all.
        if system:
            request["system"] = [{"text": system}]
        try:
            response = self._client.converse(**request)
        except ClientError as exc:
            raise ProviderError(
                f"{spec.model}: {exc.response['Error']['Code']}: "
                f"{exc.response['Error']['Message']}"
            ) from exc

        usage = response["usage"]
        blocks = response["output"]["message"]["content"]
        # Some models lead with a reasoning block; take the first text block.
        text = next((b["text"] for b in blocks if "text" in b), "")
        return Completion(
            text=text,
            model=spec.model,
            tokens_in=usage["inputTokens"],
            tokens_out=usage["outputTokens"],
            tokens_cached=usage.get("cacheReadInputTokens", 0),
            latency_ms=int((time.monotonic() - started) * 1000),
            stop_reason=response.get("stopReason", "unknown"),
        )

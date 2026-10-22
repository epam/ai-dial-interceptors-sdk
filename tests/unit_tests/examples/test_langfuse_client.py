import time
from collections.abc import Sequence
from typing import cast

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from aidial_interceptors_sdk.examples.chat_completion.langfuse.langfuse_client import (
    LangfuseClient,
)

STREAM_DURATION = 0.2

exporter = InMemorySpanExporter()


class OfflineLangfuseClient(LangfuseClient):
    def connect(self):
        return Langfuse(
            public_key="pk",
            secret_key="sk",  # noqa: S106
            span_exporter=exporter,
        )


def create_client(is_model: bool) -> OfflineLangfuseClient:
    return OfflineLangfuseClient(
        session_id="sess-1",
        tags=["gpt-4o", "gpt-4o-deployment"],
        request_messages=[{"role": "user", "content": "hi"}],
        model_name="gpt-4o",
        deployment_id="gpt-4o-deployment",
        user_id="someone@epam.com",
        metadata={"x_conversation_id": "conv-1", "is_model": is_model},
        is_model=is_model,
    )


@pytest.mark.parametrize(
    "is_model,expected_name,expected_type",
    [
        (True, "gpt-4o", "generation"),
        (False, "Processing", "span"),
    ],
)
def test_observation(is_model: bool, expected_name: str, expected_type: str):
    exporter.clear()

    client = create_client(is_model)
    client.start()
    time.sleep(STREAM_DURATION)
    client.finish({"role": "assistant", "content": "hello"})

    spans = exporter.get_finished_spans()
    assert len(spans) == 1

    span = spans[0]
    attributes = dict(span.attributes or {})

    assert span.name == expected_name
    assert attributes["langfuse.observation.type"] == expected_type
    assert attributes.get("langfuse.observation.model.name") == (
        "gpt-4o" if is_model else None
    )

    assert attributes["session.id"] == "sess-1"
    assert attributes["user.id"] == "someone@epam.com"
    tags = cast(Sequence[str], attributes["langfuse.trace.tags"])
    assert list(tags) == ["gpt-4o", "gpt-4o-deployment"]
    assert attributes["langfuse.trace.name"] == "gpt-4o"
    assert attributes["langfuse.trace.metadata.x_conversation_id"] == "conv-1"

    assert "hi" in str(attributes["langfuse.observation.input"])
    assert "hello" in str(attributes["langfuse.observation.output"])


def test_observation_measures_the_stream():
    exporter.clear()

    client = create_client(is_model=True)
    client.start()
    time.sleep(STREAM_DURATION)
    client.finish({"role": "assistant", "content": "hello"})

    span = exporter.get_finished_spans()[0]
    assert span.start_time is not None and span.end_time is not None
    assert (span.end_time - span.start_time) / 1e9 >= STREAM_DURATION


def test_finish_without_start_is_a_noop():
    exporter.clear()

    create_client(is_model=True).finish({"role": "assistant"})

    assert exporter.get_finished_spans() == ()

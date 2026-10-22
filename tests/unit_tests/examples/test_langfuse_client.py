from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import cast

import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from aidial_interceptors_sdk.examples.chat_completion.langfuse.langfuse_client import (
    LangfuseClient,
)

start_time = datetime(2026, 10, 22, 12, 0, 0)
end_time = start_time + timedelta(seconds=4, milliseconds=200)

exporter = InMemorySpanExporter()


class OfflineLangfuseClient(LangfuseClient):
    """Keeps the real Langfuse calls, collects the spans in memory."""

    def connect(self):
        return Langfuse(
            public_key="pk",
            secret_key="sk",  # noqa: S106
            span_exporter=exporter,
        )


@pytest.mark.parametrize(
    "is_model,expected_name,expected_type",
    [
        (True, "gpt-4o", "generation"),
        (False, "Processing", "span"),
    ],
)
def test_transmit(is_model: bool, expected_name: str, expected_type: str):
    exporter.clear()

    OfflineLangfuseClient(
        session_id="sess-1",
        tags=["gpt-4o", "gpt-4o-deployment"],
        request_messages=[{"role": "user", "content": "hi"}],
        response_message={"role": "assistant", "content": "hello"},
        model_name="gpt-4o",
        deployment_id="gpt-4o-deployment",
        start_time=start_time,
        end_time=end_time,
        user_id="someone@epam.com",
        metadata={"x_conversation_id": "conv-1", "is_model": is_model},
        is_model=is_model,
    ).transmit()

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
    assert "hi" in str(attributes["langfuse.trace.input"])
    assert "hello" in str(attributes["langfuse.trace.output"])

    assert (
        attributes["langfuse.observation.metadata.start_time"]
        == start_time.isoformat()
    )
    assert (
        attributes["langfuse.observation.metadata.end_time"]
        == end_time.isoformat()
    )

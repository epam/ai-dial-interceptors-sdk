from datetime import datetime

from aidial_sdk.pydantic_v1 import BaseModel
from langfuse import Langfuse, propagate_attributes


class LangfuseClient(BaseModel):
    session_id: str
    tags: list[str]
    request_messages: list
    response_message: dict
    model_name: str = ""
    deployment_id: str = ""
    start_time: datetime
    end_time: datetime
    user_id: str | None
    metadata: dict = {}
    is_model: bool

    def connect(self):
        return Langfuse()

    def transmit(self):
        conn = self.connect()
        with propagate_attributes(
            trace_name=self.model_name,
            session_id=self.session_id,
            tags=self.tags,
            user_id=self.user_id,
            metadata=self.metadata,
        ):
            if self.is_model:
                observation = conn.start_observation(
                    name=self.model_name,
                    as_type="generation",
                    model=self.model_name,
                    input=self.request_messages,
                    output=self.response_message,
                    metadata=self._timings,
                )
            else:
                observation = conn.start_observation(
                    name="Processing",
                    as_type="span",
                    input=self.request_messages,
                    output=self.response_message,
                    metadata=self._timings,
                )
            observation.set_trace_io(
                input=self.request_messages, output=self.response_message
            )
            observation.end()
        conn.flush()
        return

    @property
    def _timings(self) -> dict:
        # An observation is timed by Langfuse's own clock and `start_observation`
        # takes no start time, so the stream's real interval is carried here.
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }

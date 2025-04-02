from datetime import datetime
from typing import Optional

from aidial_sdk.pydantic_v1 import BaseModel
from langfuse import Langfuse


class LangfuseClient(BaseModel):
    session_id: str
    tags: list[str]
    request_messages: list
    response_message: dict
    model_name: str = ""
    deployment_id: str = ""
    start_time: datetime
    end_time: datetime
    user_id: Optional[str]
    metadata: dict = {}
    is_model: bool

    def connect(self):
        return Langfuse()

    def transmit(self):
        conn = self.connect()
        trace = conn.trace(
            name=self.model_name,
            session_id=self.session_id,
            tags=self.tags,
            input=self.request_messages,
            output=self.response_message,
            user_id=self.user_id,
            metadata=self.metadata,
        )
        if self.is_model:
            trace.generation(
                model=self.model_name,
                input=self.request_messages,
                output=self.response_message,
                start_time=self.start_time,
                end_time=self.end_time,
            )
        else:
            trace.span(
                name="Processing",
                input=self.request_messages,
                output=self.response_message,
                start_time=self.start_time,
                end_time=self.end_time,
            )
        conn.flush()
        return

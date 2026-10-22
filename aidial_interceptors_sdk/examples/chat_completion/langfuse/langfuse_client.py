from typing import Any

from aidial_sdk.pydantic_v1 import BaseModel, PrivateAttr
from langfuse import Langfuse, propagate_attributes


class LangfuseClient(BaseModel):
    session_id: str
    tags: list[str]
    request_messages: list
    model_name: str = ""
    deployment_id: str = ""
    user_id: str | None
    metadata: dict = {}
    is_model: bool

    _connection: Any = PrivateAttr(None)
    _observation: Any = PrivateAttr(None)

    def connect(self):
        return Langfuse()

    def start(self):
        """
        Opens the observation.

        Langfuse times an observation by its own clock, so this must be called
        when the stream starts for the reported duration to be the real one.
        """
        self._connection = self.connect()

        # The attributes are stamped onto the observation as it is created,
        # so the context only has to be open for that call.
        with propagate_attributes(
            trace_name=self.model_name,
            session_id=self.session_id,
            tags=self.tags,
            user_id=self.user_id,
            metadata=self.metadata,
        ):
            if self.is_model:
                self._observation = self._connection.start_observation(
                    name=self.model_name,
                    as_type="generation",
                    model=self.model_name,
                    input=self.request_messages,
                )
            else:
                self._observation = self._connection.start_observation(
                    name="Processing",
                    as_type="span",
                    input=self.request_messages,
                )

    def finish(self, response_message: dict):
        """
        Closes the observation opened by `start`, ending the interval it
        measures. Does nothing when the observation was never opened.
        """
        if self._connection is None or self._observation is None:
            return

        self._observation.update(output=response_message)
        self._observation.end()
        self._connection.flush()

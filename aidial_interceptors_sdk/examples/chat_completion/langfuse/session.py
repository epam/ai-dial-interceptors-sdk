import uuid

from aidial_sdk.pydantic_v1 import BaseModel, PrivateAttr

SESSION_ID_KEY = "langfuse_session_id"


class Session(BaseModel):
    session_id: str = ""
    _added_session_id: bool = PrivateAttr(False)

    @classmethod
    def create(cls, messages: list[dict]) -> "Session":
        messages = list(
            filter(
                lambda msg: msg.get("custom_content")
                and msg["custom_content"].get("state")
                and SESSION_ID_KEY in msg["custom_content"]["state"],
                messages,
            )
        )
        if messages:
            session_id = messages[0]["custom_content"]["state"][SESSION_ID_KEY]
        else:
            session_id = str(uuid.uuid4())
        return cls(session_id=session_id)

    def add_session_id_to_message(self, message: dict) -> dict:
        if not self._added_session_id:
            message.setdefault("custom_content", {}).setdefault("state", {})[
                SESSION_ID_KEY
            ] = self.session_id
            self._added_session_id = True
        return message

    def remove_session_id_from_message(self, message: dict) -> dict:
        if (
            message.get("custom_content", {})
            .get("state", {})
            .get(SESSION_ID_KEY)
        ):
            del message["custom_content"]["state"][SESSION_ID_KEY]
        if message.get("custom_content", {}).get("state") == {}:
            del message["custom_content"]
        return message

    def remove_session_id_from_messages(
        self, messages: list[dict]
    ) -> list[dict]:
        return [self.remove_session_id_from_message(msg) for msg in messages]

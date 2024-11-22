from tests.utils.json import Check, has_type


def create_chunk_checker(
    *,
    stream: bool,
    id_check: Check = has_type(str),
    created_check: Check = has_type(int)
):
    def _checker(delta: dict = {}, finish_reason: str | None = None):
        object = "chat.completion.chunk" if stream else "chat.completion"
        message_key = "delta" if stream else "message"

        return {
            "id": id_check,
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "index": 0,
                    message_key: delta,
                }
            ],
            "created": created_check,
            "object": object,
            "usage": None,
        }

    return _checker

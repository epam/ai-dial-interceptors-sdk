from typing import Any, Self

from aidial_sdk.pydantic_v1 import BaseModel

from aidial_interceptors_sdk.chat_completion.index_mapper import IndexMapper


class ChoiceContext(BaseModel):
    index: int
    stage_index_mapper: IndexMapper[int]


class ElementPath(BaseModel):
    # Only for responses
    response_ctx: Any | None = None
    choice_ctx: ChoiceContext | None = None

    # Only for requests
    message_idx: int | None = None

    # Both for requests and responses
    stage_idx: int | None = None
    attachment_idx: int | None = None

    def with_response_ctx(self, response_ctx: Any) -> Self:
        return self.copy(update={"response_ctx": response_ctx})

    def with_choice_ctx(self, choice_ctx: ChoiceContext) -> Self:
        return self.copy(update={"choice_ctx": choice_ctx})

    def with_message_idx(self, message_idx: int) -> Self:
        return self.copy(update={"message_idx": message_idx})

    def with_stage_idx(self, stage_idx: int) -> Self:
        return self.copy(update={"stage_idx": stage_idx})

    def with_attachment_idx(self, attachment_idx: int) -> Self:
        return self.copy(update={"attachment_idx": attachment_idx})

    @property
    def choice_idx(self) -> int | None:
        return self.choice_ctx.index if self.choice_ctx else None

    @property
    def choice_stage_index_mapper(self) -> IndexMapper[int] | None:
        return self.choice_ctx.stage_index_mapper if self.choice_ctx else None

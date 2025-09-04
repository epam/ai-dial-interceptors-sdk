"""
All kinds of logic which is a good candidate
to be moved eventually to the SDK itself.
"""

import json
import logging
from typing import Type, TypeVar

import pydantic
from aidial_sdk.chat_completion import Request, Response
from aidial_sdk.chat_completion.chunks import ArbitraryChunk, BaseChunk
from aidial_sdk.exceptions import RequestValidationError
from pydantic import BaseModel

from aidial_interceptors_sdk.utils._string import decapitalize

_log = logging.getLogger(__name__)


def send_chunk_to_response(response: Response, chunk: BaseChunk | dict):
    if isinstance(chunk, dict):
        for choice in chunk.get("choices") or []:
            if (index := choice.get("index")) is not None:
                response._last_choice_index = max(
                    response._last_choice_index, index + 1
                )
        response._queue.put_nowait(ArbitraryChunk(chunk=chunk))
    else:
        response._queue.put_nowait(chunk)


_T = TypeVar("_T", bound=BaseModel)


def parse_interceptor_configuration(
    request: Request, cls: Type[_T] | None
) -> _T | None:
    _conf_key = "interceptor_configuration"

    config: dict | None = None
    if cf := request.custom_fields:
        config = cf.dict().get(_conf_key)

    if config is not None:
        _log.debug(f"interceptor configuration: {json.dumps(config)}")

    match (cls, config):
        case (None, None):
            return None
        case (None, _):
            raise RequestValidationError(
                f"The interceptor doesn't have configuration, but it was provided in the chat completion request. Path: 'custom_fields.{_conf_key}'"
            )
        case (_, _):
            try:
                conf = {} if config is None else config
                return cls.parse_obj(conf)
            except pydantic.ValidationError as e:
                error = e.errors()[0]
                path = ".".join(map(str, error["loc"]))
                msg = f"Invalid request. Path: 'custom_fields.{_conf_key}.{path}', error: {decapitalize(error['msg'])}"

                raise RequestValidationError(msg)

from typing import Type

from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionInterceptor,
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.embeddings.base import (
    EmbeddingsInterceptor,
    EmbeddingsNoOpInterceptor,
)
from aidial_interceptors_sdk.examples.chat_completion import (
    BlacklistedWordsInterceptor as ChatBlacklistedWordsInterceptor,
)
from aidial_interceptors_sdk.examples.chat_completion import (
    CachingInterceptor as ChatCachingInterceptor,
)
from aidial_interceptors_sdk.examples.chat_completion import (
    ImageWatermarkInterceptor,
    PIIAnonymizerInterceptor,
    PirateInterceptor,
    RejectExternalLinksInterceptor,
    ReplicatorInterceptor,
    StatisticsReporterInterceptor,
)
from aidial_interceptors_sdk.examples.embeddings import (
    BlacklistedWordsInterceptor as EmbeddingsBlacklistedWordsInterceptor,
)
from aidial_interceptors_sdk.examples.embeddings import (
    NormalizeVectorInterceptor,
    ProjectVectorInterceptor,
)

chat_completion_interceptors: dict[str, Type[ChatCompletionInterceptor]] = {
    "reply-as-pirate": PirateInterceptor,
    "reject-external-links": RejectExternalLinksInterceptor,
    "image-watermark": ImageWatermarkInterceptor,
    "statistics-reporter": StatisticsReporterInterceptor,
    "pii-anonymizer": PIIAnonymizerInterceptor,
    "replicator:{n:int}": ReplicatorInterceptor,
    "reject-blacklisted-words": ChatBlacklistedWordsInterceptor,
    "cache": ChatCachingInterceptor,
    "no-op": ChatCompletionNoOpInterceptor,
}

embeddings_interceptors: dict[str, Type[EmbeddingsInterceptor]] = {
    "reject-blacklisted-words": EmbeddingsBlacklistedWordsInterceptor,
    "normalize-vector": NormalizeVectorInterceptor,
    "project-vector:{dim:int}": ProjectVectorInterceptor,
    "no-op": EmbeddingsNoOpInterceptor,
}

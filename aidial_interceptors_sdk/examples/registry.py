from aidial_interceptors_sdk.chat_completion.base import (
    ChatCompletionNoOpInterceptor,
)
from aidial_interceptors_sdk.embeddings.base import (
    EmbeddingsNoOpInterceptor,
)
from aidial_interceptors_sdk.examples.app_factory import Interceptors
from aidial_interceptors_sdk.examples.chat_completion import (
    BlacklistedWordsInterceptor as ChatBlacklistedWordsInterceptor,
)
from aidial_interceptors_sdk.examples.chat_completion import (
    CachingInterceptor as ChatCachingInterceptor,
)
from aidial_interceptors_sdk.examples.chat_completion import (
    GoogleDLPAnonymizerInterceptor,
    ImageWatermarkInterceptor,
    LangfuseInterceptor,
    PirateInterceptor,
    RejectExternalLinksInterceptor,
    ReplicatorInterceptor,
    SpacyAnonymizerInterceptor,
    StatisticsReporterInterceptor,
    WhitespaceAccumulatorInterceptor,
)
from aidial_interceptors_sdk.examples.embeddings import (
    BlacklistedWordsInterceptor as EmbeddingsBlacklistedWordsInterceptor,
)
from aidial_interceptors_sdk.examples.embeddings import (
    NormalizeVectorInterceptor,
    ProjectVectorInterceptor,
)

EXAMPLE_INTERCEPTORS: Interceptors = Interceptors(
    chat_completions={
        "reply-as-pirate": PirateInterceptor,
        "reject-external-links": RejectExternalLinksInterceptor,
        "image-watermark": ImageWatermarkInterceptor,
        "statistics-reporter": StatisticsReporterInterceptor,
        "pii-anonymizer": SpacyAnonymizerInterceptor,
        "spacy-anonymizer": SpacyAnonymizerInterceptor,
        "google-dlp-anonymizer": GoogleDLPAnonymizerInterceptor,
        "replicator:{n:int}": ReplicatorInterceptor,
        "reject-blacklisted-words": ChatBlacklistedWordsInterceptor,
        "cache": ChatCachingInterceptor,
        "langfuse": LangfuseInterceptor,
        "no-op": ChatCompletionNoOpInterceptor,
        "whitespace-accumulator": WhitespaceAccumulatorInterceptor,
    },
    embeddings={
        "reject-blacklisted-words": EmbeddingsBlacklistedWordsInterceptor,
        "normalize-vector": NormalizeVectorInterceptor,
        "project-vector:{dim:int}": ProjectVectorInterceptor,
        "no-op": EmbeddingsNoOpInterceptor,
    },
)

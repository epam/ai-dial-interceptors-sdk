from typing import List

from typing_extensions import override

from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor
from aidial_interceptors_sdk.examples.utils.embedding_encoding import (
    base64_to_vector,
    vector_to_base64,
)


def normalize(vec: List[float]) -> List[float]:
    norm = sum(x**2 for x in vec) ** 0.5
    return [x / norm for x in vec]


class NormalizeVectorInterceptor(EmbeddingsInterceptor):
    @override
    async def modify_embedding(
        self, embedding: str | List[float]
    ) -> str | List[float]:
        if isinstance(embedding, str):
            vec = base64_to_vector(embedding)
            vec = normalize(vec)
            return vector_to_base64(vec)
        else:
            return normalize(embedding)

from typing_extensions import override

from aidial_interceptors_sdk.embeddings.base import EmbeddingsInterceptor
from aidial_interceptors_sdk.examples.utils.embedding_encoding import (
    base64_to_vector,
    vector_to_base64,
)


def project(vec: list[float], dim: int) -> list[float]:
    diff = dim - len(vec)
    if diff == 0:
        return vec
    elif diff > 0:
        return vec + [0.0] * diff
    else:
        return vec[:dim]


class ProjectVectorInterceptor(EmbeddingsInterceptor):
    dim: int

    @override
    async def modify_embedding(
        self, embedding: str | list[float]
    ) -> str | list[float]:
        if isinstance(embedding, str):
            vec = base64_to_vector(embedding)
            vec = project(vec, self.dim)
            return vector_to_base64(vec)
        else:
            return project(embedding, self.dim)

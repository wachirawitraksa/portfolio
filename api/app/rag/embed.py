"""Text to a vector with no model and no network: hashed words plus hashed character trigrams.

Character trigrams need no Thai word cutting and forgive small typing mistakes; the words carry the
exact meaning. It works offline. If quality is not enough, swap this one function for a multilingual
embedding model (BGE-M3); the rest of the search does not care how the vector was made."""
import math
import re
import zlib

from ..models import EMBED_DIM

WORD_WEIGHT = 1.0
TRIGRAM_WEIGHT = 0.5


def _bucket(feature: str) -> tuple[int, float]:
    """Which slot a feature lands in, and a +1/-1 sign so unrelated features cancel instead of piling up."""
    h = zlib.crc32(feature.encode("utf-8"))
    return h % EMBED_DIM, 1.0 if (h >> 31) & 1 else -1.0


def embed(text: str, words: list[str] | None = None) -> list[float]:
    """`text` must already be normalized. `words` are its tokens (Thai cut by the tokenizer) if known."""
    vector = [0.0] * EMBED_DIM
    counts: dict[str, float] = {}
    for word in words if words is not None else text.split():
        counts["w:" + word] = counts.get("w:" + word, 0.0) + WORD_WEIGHT
    squeezed = re.sub(r"\s+", " ", text)
    for i in range(len(squeezed) - 2):
        gram = squeezed[i : i + 3]
        if gram.strip():
            counts["g:" + gram] = counts.get("g:" + gram, 0.0) + TRIGRAM_WEIGHT
    for feature, count in counts.items():
        slot, sign = _bucket(feature)
        vector[slot] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector

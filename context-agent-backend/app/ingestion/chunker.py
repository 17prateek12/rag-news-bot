import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    sentences = _SENTENCE_SPLIT.split(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence) > chunk_size:
            start = 0
            while start < len(sentence):
                chunks.append(sentence[start : start + chunk_size])
                start += chunk_size - overlap
            current = ""
        else:
            current = sentence

    if current:
        chunks.append(current)

    if overlap <= 0 or len(chunks) < 2:
        return chunks

    overlapped: list[str] = [chunks[0]]
    for idx in range(1, len(chunks)):
        prev_tail = chunks[idx - 1][-overlap:]
        overlapped.append(f"{prev_tail} {chunks[idx]}".strip())
    return overlapped

import hashlib
from dataclasses import dataclass
from typing import Iterable, List

from datasketch import MinHash, MinHashLSH


class ExactDeduplicator:
    def __init__(self) -> None:
        self._seen = set()

    def is_duplicate(self, text: str) -> bool:
        h = hashlib.blake2b(text.encode("utf-8", errors="ignore"), digest_size=16).hexdigest()
        if h in self._seen:
            return True
        self._seen.add(h)
        return False


@dataclass
class SemanticDeduplicator:
    threshold: float = 0.8
    num_perm: int = 128

    def __post_init__(self) -> None:
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self.counter = 0

    def _signature(self, text: str) -> MinHash:
        mh = MinHash(num_perm=self.num_perm)
        for token in text.lower().split():
            mh.update(token.encode("utf-8", errors="ignore"))
        return mh

    def is_duplicate(self, text: str) -> bool:
        sig = self._signature(text)
        matches = self.lsh.query(sig)
        if matches:
            return True
        key = f"doc-{self.counter}"
        self.lsh.insert(key, sig)
        self.counter += 1
        return False


def dedup_stream(texts: Iterable[str], semantic: bool = False) -> List[str]:
    deduper = SemanticDeduplicator() if semantic else ExactDeduplicator()
    return [txt for txt in texts if not deduper.is_duplicate(txt)]

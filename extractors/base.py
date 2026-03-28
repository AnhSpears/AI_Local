from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass
class Document:
    text: str
    meta: Dict


class BaseExtractor:
    source_name: str = "unknown"

    def stream(self) -> Iterable[Document]:
        raise NotImplementedError
